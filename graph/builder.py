"""
Module de construction de graphe pour l'analyse des transactions Kaspa
Construit un graphe orienté où les nœuds sont des adresses et les arêtes sont des transactions
"""
import networkx as nx
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple

from kaspa.client import KaspaClient

class GraphBuilder:
    """
    Constructeur de graphe pour l'analyse des transactions Kaspa
    """
    
    def __init__(self, kaspa_client: KaspaClient):
        """
        Initialise le constructeur de graphe
        
        Args:
            kaspa_client: Instance du client Kaspa pour les requêtes API
        """
        self.client = kaspa_client
        self.graph = nx.DiGraph()
        self.address_info_cache = {}  # Cache pour éviter des requêtes API répétées
        
    async def build_transaction_graph(
        self, 
        start_address: str, 
        depth: int = 2, 
        min_amount: Optional[float] = None,
        max_addresses: int = 1000
    ) -> nx.DiGraph:
        """
        Construit un graphe complet à partir d'une adresse de départ
        
        Args:
            start_address: Adresse Kaspa de départ
            depth: Profondeur de l'analyse (nombre de sauts)
            min_amount: Montant minimum à considérer (en KAS)
            max_addresses: Nombre maximum d'adresses à inclure
            
        Returns:
            Graphe orienté NetworkX
        """
        # Réinitialiser le graphe
        self.graph = nx.DiGraph()
        visited_addresses = set()
        
        # Ajouter le nœud de départ
        address_info = await self._get_address_info(start_address)
        
        # Supprimer la clé 'address' du dictionnaire pour éviter le conflit
        address_info_copy = address_info.copy()
        if 'address' in address_info_copy:
            del address_info_copy['address']
            
        self._add_node(start_address, is_start=True, **address_info_copy)
        
        # Construire le graphe de manière récursive
        await self._build_graph_recursive(
            start_address, 
            visited_addresses, 
            current_depth=0, 
            max_depth=depth,
            min_amount=min_amount,
            max_addresses=max_addresses
        )
        
        # Calculer des métriques de base pour chaque nœud
        self._calculate_node_metrics()
        
        return self.graph
    
    async def _build_graph_recursive(
        self, 
        address: str, 
        visited_addresses: Set[str], 
        current_depth: int, 
        max_depth: int,
        min_amount: Optional[float] = None,
        max_addresses: int = 1000
    ) -> None:
        """
        Construit le graphe récursivement en suivant les transactions
        
        Args:
            address: Adresse courante
            visited_addresses: Ensemble des adresses déjà visitées
            current_depth: Profondeur actuelle dans la récursion
            max_depth: Profondeur maximale à atteindre
            min_amount: Montant minimum à considérer (en KAS)
            max_addresses: Nombre maximum d'adresses à inclure
        """
        if current_depth >= max_depth or address in visited_addresses:
            return
            
        if len(visited_addresses) >= max_addresses:
            return
            
        visited_addresses.add(address)
        
        # Récupérer les transactions pour cette adresse
        transactions = await self.client.get_address_transactions(address)
        
        # Log pour le débogage
        import logging
        logger = logging.getLogger("graph_builder")
        logger.debug(f"Récupération de {len(transactions)} transactions pour {address}")
        
        # Analyser chaque transaction
        for tx in transactions:
            # Format attendu : {'transaction_id': '...', 'outputs': [{'address': '...', 'amount': 123}]}
            tx_id = tx.get('transaction_id', tx.get('txid', ''))
            outputs = tx.get('outputs', [])
            
            # Journaliser le format pour debug
            if not outputs and 'outputs' in tx:
                logger.debug(f"Format d'outputs inattendu: {tx['outputs']}")
            elif not outputs:
                logger.debug(f"Clés disponibles dans la transaction: {list(tx.keys())}")
                # Essayer de trouver d'autres champs qui pourraient contenir les sorties
                for key, value in tx.items():
                    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                        logger.debug(f"Champ potentiel pour les outputs: {key}")
                        if 'address' in value[0] or 'amount' in value[0] or 'value' in value[0]:
                            logger.debug(f"Utilisation du champ {key} comme outputs")
                            outputs = value
                            break
            
            # Convertir le montant en KAS si nécessaire
            scaling_factor = 1e8  # Conversion Sompi -> KAS
            
            # Pour chaque sortie de transaction
            for output in outputs:
                output_address = output.get('address', output.get('script_public_key_address', ''))
                amount_raw = output.get('amount', output.get('value', 0))
                
                # Convertir le montant
                amount = amount_raw / scaling_factor
                
                # Ignorer les transactions vers soi-même et sous le montant minimum
                if not output_address or output_address == address:
                    continue
                
                if min_amount is not None and amount < min_amount:
                    continue
                
                # Ajouter le nœud de destination s'il n'existe pas
                if output_address not in self.graph:
                    address_info = await self._get_address_info(output_address)
                    # Supprimer la clé 'address' pour éviter le conflit
                    address_info_copy = address_info.copy()
                    if 'address' in address_info_copy:
                        del address_info_copy['address']
                    self._add_node(output_address, **address_info_copy)
                
                # Ajouter l'arête pour la transaction
                self._add_edge(
                    address, 
                    output_address, 
                    txid=tx_id,
                    amount=amount,
                    timestamp=tx.get('block_time', tx.get('timestamp', 0))
                )
                
                # Récursion pour l'adresse de destination
                await self._build_graph_recursive(
                    output_address,
                    visited_addresses,
                    current_depth + 1,
                    max_depth,
                    min_amount,
                    max_addresses
                )
    
    def _add_node(self, address: str, is_start: bool = False, **attributes) -> None:
        """
        Ajoute un nœud au graphe avec ses attributs
        
        Args:
            address: Adresse Kaspa
            is_start: Indique s'il s'agit de l'adresse de départ
            **attributes: Attributs supplémentaires du nœud
        """
        # Attributs de base pour chaque nœud
        node_attrs = {
            "address": address,
            "is_start": is_start,
            "is_exchange": attributes.get("is_exchange", False),
            "balance": attributes.get("balance", 0),
            "total_received": 0,  # Sera calculé plus tard
            "total_sent": 0,      # Sera calculé plus tard
            "transaction_count": attributes.get("transactions", 0)
        }
        
        self.graph.add_node(address, **node_attrs)
    
    def _add_edge(
        self, 
        source: str, 
        target: str, 
        txid: str,
        amount: float,
        timestamp: int
    ) -> None:
        """
        Ajoute une arête au graphe représentant une transaction
        
        Args:
            source: Adresse source
            target: Adresse destination
            txid: ID de la transaction
            amount: Montant de la transaction
            timestamp: Horodatage de la transaction
        """
        import logging
        logger = logging.getLogger("graph_builder")
        
        # Vérifier et corriger le timestamp si nécessaire
        try:
            if timestamp < 0 or timestamp > 4102444800:  # Après 2100, probablement invalide
                logger.warning(f"Timestamp invalide détecté: {timestamp}, utilisation de 0")
                timestamp = 0
                date_str = "Date inconnue"
            else:
                from datetime import datetime
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError) as e:
            logger.warning(f"Erreur de conversion de timestamp {timestamp}: {str(e)}")
            timestamp = 0
            date_str = "Date invalide"
        
        # Attributs de l'arête
        edge_attrs = {
            "txid": txid,
            "amount": amount,
            "timestamp": timestamp,
            "date": date_str
        }
        
        # Ajouter ou mettre à jour l'arête
        if self.graph.has_edge(source, target):
            # S'il y a déjà une transaction entre ces adresses, créer une liste
            edge_data = self.graph[source][target]
            
            if "transactions" not in edge_data:
                # Convertir l'arête simple en liste de transactions
                existing_tx = {
                    "txid": edge_data["txid"],
                    "amount": edge_data["amount"],
                    "timestamp": edge_data["timestamp"],
                    "date": edge_data["date"]
                }
                edge_data["transactions"] = [existing_tx]
                
                # Supprimer les attributs individuels
                del edge_data["txid"]
                del edge_data["amount"]
                del edge_data["timestamp"]
                del edge_data["date"]
            
            # Ajouter la nouvelle transaction
            edge_data["transactions"].append({
                "txid": txid,
                "amount": amount,
                "timestamp": timestamp,
                "date": date_str
            })
            
            # Mettre à jour le montant total
            edge_data["total_amount"] = edge_data.get("total_amount", 0) + amount
            
        else:
            # Première transaction entre ces adresses
            self.graph.add_edge(source, target, **edge_attrs)
    
    def _calculate_node_metrics(self) -> None:
        """
        Calcule les métriques de base pour chaque nœud du graphe
        """
        for node in self.graph.nodes:
            # Calculer le montant total envoyé
            total_sent = 0
            for _, target, data in self.graph.out_edges(node, data=True):
                if "amount" in data:
                    total_sent += data["amount"]
                elif "total_amount" in data:
                    total_sent += data["total_amount"]
            
            # Calculer le montant total reçu
            total_received = 0
            for source, _, data in self.graph.in_edges(node, data=True):
                if "amount" in data:
                    total_received += data["amount"]
                elif "total_amount" in data:
                    total_received += data["total_amount"]
            
            # Mettre à jour les attributs du nœud
            self.graph.nodes[node]["total_sent"] = total_sent
            self.graph.nodes[node]["total_received"] = total_received
            
            # Calculer le nombre de connections
            self.graph.nodes[node]["in_degree"] = self.graph.in_degree(node)
            self.graph.nodes[node]["out_degree"] = self.graph.out_degree(node)
    
    async def _get_address_info(self, address: str) -> Dict[str, Any]:
        """
        Récupère les informations sur une adresse (avec mise en cache)
        
        Args:
            address: Adresse Kaspa
            
        Returns:
            Informations sur l'adresse
        """
        if address in self.address_info_cache:
            return self.address_info_cache[address]
        
        try:
            address_info = await self.client.get_address_info(address)
            self.address_info_cache[address] = address_info
            return address_info
        except Exception as e:
            # En cas d'erreur, retourner des informations minimales
            return {
                "balance": 0,
                "transactions": 0,
                "is_exchange": False
            }
    
    def export_graph_data(self) -> Dict[str, Any]:
        """
        Exporte les données du graphe dans un format adapté à la visualisation
        
        Returns:
            Dictionnaire avec les nœuds et les arêtes formatés pour D3.js
        """
        nodes = []
        links = []
        
        # Convertir les nœuds
        for node_id, attrs in self.graph.nodes(data=True):
            node_data = {
                "id": node_id,
                "label": self._format_address_label(node_id),
                **attrs
            }
            nodes.append(node_data)
        
        # Convertir les arêtes
        for source, target, attrs in self.graph.edges(data=True):
            edge_data = {
                "source": source,
                "target": target,
                **attrs
            }
            links.append(edge_data)
        
        return {
            "nodes": nodes,
            "links": links,
            "metrics": {
                "node_count": len(nodes),
                "edge_count": len(links),
                "total_volume": sum(link.get("amount", 0) for link in links if "amount" in link)
            }
        }
    
    @staticmethod
    def _format_address_label(address: str) -> str:
        """
        Formate une adresse Kaspa pour l'affichage
        
        Args:
            address: Adresse Kaspa complète
            
        Returns:
            Version abrégée de l'adresse
        """
        if not address or not isinstance(address, str):
            return "Unknown"
            
        # Format: "kaspa:qz...at" (les 3 premiers et 3 derniers caractères)
        if len(address) > 10:
            return f"{address[:9]}...{address[-3:]}"
        return address