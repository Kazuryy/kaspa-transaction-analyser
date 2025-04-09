#!/usr/bin/env python3
"""
Kaspa Transaction Analyzer - Application principale
Point d'entrée qui démarre le serveur FastAPI et sert l'interface web
"""
import os
import uvicorn
import logging
import traceback
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Configuration de la journalisation
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kaspa_analyzer")

# Import des modules internes
from kaspa.client import KaspaClient
from graph.builder import GraphBuilder
from graph.analysis import GraphAnalyzer

# Création de l'application FastAPI
app = FastAPI(
    title="Kaspa Transaction Analyzer",
    description="Outil d'analyse forensique des transactions Kaspa",
    version="1.0.0"
)

# Configuration du CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour le développement seulement, à restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration du client Kaspa
kaspa_client = KaspaClient("https://api.kaspa.org")

# Montage des fichiers statiques (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Modèles de données pour les requêtes
class AnalysisRequest(BaseModel):
    """Modèle pour demander une analyse de transactions"""
    start_address: str = Field(..., description="Adresse Kaspa de départ")
    depth: int = Field(2, ge=1, le=5, description="Profondeur d'analyse (nombre de niveaux)")
    min_amount: Optional[float] = Field(None, description="Montant minimum à considérer en KAS")
    max_transactions: int = Field(1000, ge=10, le=5000, description="Nombre maximum de transactions à analyser")
    include_exchanges: bool = Field(True, description="Identifier les exchanges connus et potentiels")

class GraphData(BaseModel):
    """Modèle pour les données de graphe retournées"""
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    suspicious_patterns: Optional[List[Dict[str, Any]]] = Field(None, description="Patterns suspects détectés")

# Routes API
@app.get("/")
async def get_index():
    """Retourne la page d'accueil"""
    logger.info("Accès à la page d'accueil")
    return FileResponse('static/index.html')

@app.post("/api/analyze", response_model=GraphData)
async def analyze_transactions(request: AnalysisRequest):
    """
    Analyse les transactions à partir d'une adresse
    et retourne un graphe de transactions
    """
    logger.info(f"Début de l'analyse pour l'adresse: {request.start_address}")
    try:
        # Récupération des transactions
        logger.debug("Tentative de récupération des transactions...")
        transactions = await kaspa_client.get_address_transactions(
            request.start_address, 
            max_results=request.max_transactions
        )
        
        logger.info(f"Récupération réussie de {len(transactions)} transactions")
        
        # Construction du graphe
        logger.debug("Construction du graphe de transactions...")
        builder = GraphBuilder(kaspa_client)
        graph = await builder.build_transaction_graph(
            start_address=request.start_address,
            depth=request.depth,
            min_amount=request.min_amount
        )
        
        logger.info(f"Graphe construit avec {len(graph.nodes)} nœuds et {len(graph.edges)} arêtes")
        
        # Analyse du graphe
        logger.debug("Analyse du graphe...")
        analyzer = GraphAnalyzer(graph)
        analyzer.calculate_centrality()
        patterns = analyzer.detect_patterns()
        
        if request.include_exchanges:
            exchanges = analyzer.identify_exchanges()
            logger.debug(f"Exchanges identifiés: {len(exchanges)}")
        
        # Préparation des données pour le frontend
        logger.debug("Préparation des données pour le frontend...")
        graph_data = analyzer.export_graph_data()
        
        logger.info("Analyse complétée avec succès")
        return GraphData(
            nodes=graph_data["nodes"],
            links=graph_data["links"],
            metrics=graph_data["metrics"],
            suspicious_patterns=graph_data.get("suspicious_patterns", [])
        )
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")

@app.get("/api/address/{address}")
async def get_address_info(address: str):
    """Récupère les informations détaillées sur une adresse"""
    logger.debug(f"Récupération des informations pour l'adresse: {address}")
    try:
        address_info = await kaspa_client.get_address_info(address)
        return address_info
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations de l'adresse: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# Gestion des erreurs 404 (ressource non trouvée)
@app.exception_handler(404)
async def not_found_handler(request, exc):
    logger.warning(f"Route non trouvée: {request.url}")
    if request.url.path.startswith('/static/'):
        return FileResponse('static/index.html')
    return {"detail": "La ressource demandée n'existe pas"}

# Ajouter cette route pour servir les fichiers JavaScript directement depuis /js/
@app.get("/js/{file_path:path}")
async def get_js(file_path: str):
    logger.debug(f"Tentative d'accès au fichier JS: {file_path}")
    return FileResponse(f"static/js/{file_path}")

# Ajouter cette route pour servir les fichiers CSS directement depuis /css/
@app.get("/css/{file_path:path}")
async def get_css(file_path: str):
    logger.debug(f"Tentative d'accès au fichier CSS: {file_path}")
    return FileResponse(f"static/css/{file_path}")

# Point d'entrée pour démarrer l'application
if __name__ == "__main__":
    logger.info("Démarrage de l'application Kaspa Transaction Analyzer")
    # Démarrage du serveur uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)