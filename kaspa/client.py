"""
Client pour l'API Kaspa
Gère les communications avec l'API Kaspa pour récupérer les transactions et informations sur les adresses
"""
import aiohttp
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union

class KaspaClient:
    """
    Client pour interagir avec l'API Kaspa
    Docs API: https://api.kaspa.org/docs#/
    """
    
    def __init__(self, api_url: str):
        """
        Initialise le client Kaspa
        
        Args:
            api_url: URL de l'API Kaspa (e.g., https://api.kaspa.org)
        """
        self.api_url = api_url
        self.logger = logging.getLogger("kaspa_client")
        self.known_exchanges = self._load_known_exchanges()
        
    async def get_address_transactions(self, address: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère les transactions associées à une adresse
        
        Args:
            address: Adresse Kaspa à analyser
            max_results: Nombre maximum de transactions à récupérer
            
        Returns:
            Liste de transactions
        """
        # Utiliser l'endpoint correct: /addresses/{kaspaAddress}/full-transactions
        endpoint = f"/addresses/{address}/full-transactions"
        params = {"limit": max_results}
        
        response = await self._make_request("GET", endpoint, params)
        
        # CORRECTION: Vérifier le type de la réponse
        # L'API retourne directement une liste de transactions et non un dictionnaire
        if isinstance(response, list):
            transactions = response
        elif isinstance(response, dict) and "transactions" in response:
            transactions = response.get("transactions", [])
        elif isinstance(response, dict) and "error" in response:
            raise Exception(f"Erreur API: {response['error']}")
        else:
            transactions = []
            
        self.logger.debug(f"Récupération de {len(transactions)} transactions pour l'adresse {address}")
        return transactions
    
    async def get_transaction_details(self, txid: str) -> Dict[str, Any]:
        """
        Récupère les détails d'une transaction spécifique
        
        Args:
            txid: Identifiant de la transaction
            
        Returns:
            Détails de la transaction
        """
        # Utiliser l'endpoint correct pour les transactions
        endpoint = f"/transactions/{txid}"
        transaction = await self._make_request("GET", endpoint)
        
        if isinstance(transaction, dict) and "error" in transaction:
            raise Exception(f"Erreur API: {transaction['error']}")
            
        return transaction
    
    async def get_address_info(self, address: str) -> Dict[str, Any]:
        """
        Récupère les informations sur une adresse
        
        Args:
            address: Adresse Kaspa
            
        Returns:
            Informations sur l'adresse (solde, nombre de tx, etc.)
        """
        # Combiner les informations de plusieurs endpoints
        balance_endpoint = f"/addresses/{address}/balance"
        tx_count_endpoint = f"/addresses/{address}/transactions-count"
        
        balance_data = await self._make_request("GET", balance_endpoint)
        tx_count_data = await self._make_request("GET", tx_count_endpoint)
        
        # Journaliser les réponses pour le débogage
        self.logger.debug(f"Réponse balance: {balance_data}")
        self.logger.debug(f"Réponse transactions count: {tx_count_data}")
        
        # Initialiser avec des valeurs par défaut
        address_info = {
            "address": address,
            "balance": 0,
            "transactions": 0,
            "is_exchange": self._check_if_exchange(address)
        }
        
        # Extraire le solde
        if isinstance(balance_data, dict):
            # Vérifier les différentes façons dont le solde pourrait être représenté
            if "balance" in balance_data:
                balance = balance_data["balance"]
                address_info["balance"] = float(balance) / 1e8  # Convertir en KAS
            else:
                self.logger.warning(f"Format de solde inattendu: {balance_data}")
        
        # Extraire le nombre de transactions
        if isinstance(tx_count_data, dict):
            # Vérifier les différentes façons dont le nombre de transactions pourrait être représenté
            if "transactionsCount" in tx_count_data:
                address_info["transactions"] = tx_count_data["transactionsCount"]
            elif "count" in tx_count_data:
                address_info["transactions"] = tx_count_data["count"]
            else:
                self.logger.warning(f"Format de nombre de transactions inattendu: {tx_count_data}")
        
        print(address_info)
        return address_info
    
    async def trace_transaction_flow(self, start_address: str, depth: int = 2) -> Dict[str, Any]:
        """
        Trace le flux de transactions à partir d'une adresse donnée
        jusqu'à une profondeur spécifiée
        
        Args:
            start_address: Adresse de départ
            depth: Profondeur de l'analyse (nombre de sauts)
            
        Returns:
            Structure de données avec le flux des transactions
        """
        visited_addresses = set()
        transaction_flow = {
            "start_address": start_address,
            "flow": {}
        }
        
        await self._recursively_trace_transactions(
            start_address, 
            transaction_flow["flow"], 
            visited_addresses, 
            current_depth=0, 
            max_depth=depth
        )
        
        return transaction_flow
    
    async def _recursively_trace_transactions(
        self, 
        address: str, 
        flow_dict: Dict, 
        visited_addresses: set, 
        current_depth: int, 
        max_depth: int
    ) -> None:
        """
        Méthode récursive pour suivre les transactions
        
        Args:
            address: Adresse courante à analyser
            flow_dict: Dictionnaire pour stocker le flux
            visited_addresses: Ensemble des adresses déjà visitées
            current_depth: Profondeur actuelle
            max_depth: Profondeur maximale à atteindre
        """
        if current_depth >= max_depth or address in visited_addresses:
            return
        
        visited_addresses.add(address)
        
        # Récupérer toutes les transactions pour cette adresse
        transactions = await self.get_address_transactions(address, max_results=50)
        
        flow_dict[address] = {
            "transactions": [],
            "next_addresses": {}
        }
        
        for tx in transactions:
            # S'assurer que nous avons des structures de données valides
            if not isinstance(tx, dict):
                self.logger.warning(f"Format de transaction inattendu: {tx}")
                continue
                
            # Analyser les outputs de la transaction
            outputs = tx.get("outputs", [])
            if not isinstance(outputs, list):
                self.logger.warning(f"Format d'outputs inattendu: {outputs}")
                continue
                
            tx_info = {
                "txid": tx.get("transactionId", tx.get("txid", "")),
                "amount": tx.get("amount", 0) / 1e8,  # Convertir en KAS
                "timestamp": tx.get("blockTime", tx.get("timestamp", 0)),
                "destinations": []
            }
            
            for output in outputs:
                if not isinstance(output, dict):
                    continue
                    
                output_address = output.get("address", "")
                if output_address and output_address != address:  # Éviter les retours à soi-même
                    output_info = {
                        "address": output_address,
                        "amount": output.get("amount", output.get("value", 0)) / 1e8  # Convertir en KAS
                    }
                    tx_info["destinations"].append(output_info)
                    
                    # Récursion pour cette destination
                    await self._recursively_trace_transactions(
                        output_info["address"],
                        flow_dict[address]["next_addresses"],
                        visited_addresses,
                        current_depth + 1,
                        max_depth
                    )
            
            flow_dict[address]["transactions"].append(tx_info)
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Effectue une requête à l'API Kaspa
        
        Args:
            method: Méthode HTTP (GET, POST, etc.)
            endpoint: Point d'entrée de l'API
            params: Paramètres de la requête
            
        Returns:
            Données de réponse
        """
        url = f"{self.api_url}{endpoint}"
        self.logger.debug(f"Requête API: {method} {url} {params}")
        
        async with aiohttp.ClientSession() as session:
            try:
                if method.upper() == "GET":
                    async with session.get(url, params=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            self.logger.error(f"Erreur API {response.status}: {error_text}")
                            return {"error": f"HTTP {response.status}: {error_text}"}
                        
                        # Journaliser un aperçu de la réponse
                        response_json = await response.json()
                        response_type = type(response_json).__name__
                        self.logger.debug(f"Réponse API de type {response_type}")
                        
                        if isinstance(response_json, list) and len(response_json) > 0:
                            self.logger.debug(f"Premier élément: {str(response_json[0])[:200]}...")
                        
                        return response_json
                        
                elif method.upper() == "POST":
                    async with session.post(url, json=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            self.logger.error(f"Erreur API {response.status}: {error_text}")
                            return {"error": f"HTTP {response.status}: {error_text}"}
                        return await response.json()
                else:
                    return {"error": f"Méthode HTTP non supportée: {method}"}
            except aiohttp.ClientError as e:
                self.logger.error(f"Erreur de requête: {str(e)}")
                return {"error": f"Erreur de connexion: {str(e)}"}
            except Exception as e:
                self.logger.error(f"Erreur inattendue: {str(e)}", exc_info=True)
                return {"error": f"Erreur inattendue: {str(e)}"}
    
    def _load_known_exchanges(self) -> Dict[str, str]:
        """
        Charge une liste d'adresses d'exchanges connues
        
        Returns:
            Dictionnaire d'adresses d'exchanges {adresse: nom_exchange}
        """
        # Dans un système production, ces données proviendraient d'une base de données
        # ou d'un service externe. Pour cet exemple, nous utilisons une liste statique.
        return {
            "kaspa:qz0c4pc68r2dd76uvhvh6l7lst5750kgc8eqv7kuf73hjkf95aeu7uy9j5aat": "Binance",
            "kaspa:qzm47s5pt54k48devr5a2kct3c4wzm0d28u2kjtexkw5xvsce6ftuzy2spg3j": "KuCoin",
            "kaspa:qp2hnzdnzpm4m9l86tufk73yz0ew6av6vv0hc52gqrq9h3w6swafw80g06qmc": "OKX",
            # Ajouter d'autres exchanges connus ici
        }
    
    def _check_if_exchange(self, address: str) -> bool:
        """
        Vérifie si une adresse appartient à un exchange connu
        
        Args:
            address: Adresse Kaspa à vérifier
            
        Returns:
            True si l'adresse appartient à un exchange, False sinon
        """
        return address in self.known_exchanges