"""
Module d'analyse de graphe pour détecter des motifs de transactions suspects
Implémente des algorithmes de détection pour identifier des schémas de blanchiment et comportements suspects
"""
import networkx as nx
import numpy as np
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

class GraphAnalyzer:
    """
    Analyseur de graphe pour détecter des motifs dans les transactions Kaspa
    """
    
    def __init__(self, graph: nx.DiGraph):
        """
        Initialise l'analyseur avec un graphe de transactions
        
        Args:
            graph: Graphe NetworkX contenant les transactions
        """
        self.graph = graph
        self.suspicious_patterns = []
        self.exchanges = set()
        self.metrics = {}
    
    def calculate_centrality(self) -> None:
        """
        Calcule différentes mesures de centralité pour les nœuds du graphe
        """
        # Calculer les mesures de centralité de base
        if len(self.graph) > 1:  # Vérifier qu'il y a au moins 2 nœuds
            try:
                # Centralité de degré
                in_degree_centrality = nx.in_degree_centrality(self.graph)
                out_degree_centrality = nx.out_degree_centrality(self.graph)
                
                # Centralité d'intermédiarité (betweenness)
                betweenness_centrality = nx.betweenness_centrality(self.graph)
                
                # Centralité d'eigenvector
                try:
                    eigenvector_centrality = nx.eigenvector_centrality(self.graph, max_iter=300)
                except:
                    # Fallback si la convergence échoue
                    eigenvector_centrality = {node: 0.0 for node in self.graph.nodes()}
                
                # Mettre à jour les attributs de chaque nœud
                for node in self.graph.nodes():
                    self.graph.nodes[node]["in_centrality"] = in_degree_centrality.get(node, 0)
                    self.graph.nodes[node]["out_centrality"] = out_degree_centrality.get(node, 0)
                    self.graph.nodes[node]["betweenness"] = betweenness_centrality.get(node, 0)
                    self.graph.nodes[node]["eigenvector"] = eigenvector_centrality.get(node, 0)
                    
                    # Calculer un score de centralité global
                    self.graph.nodes[node]["centrality_score"] = (
                        self.graph.nodes[node]["in_centrality"] +
                        self.graph.nodes[node]["out_centrality"] +
                        self.graph.nodes[node]["betweenness"] +
                        self.graph.nodes[node]["eigenvector"]
                    ) / 4.0
            
            except Exception as e:
                print(f"Erreur lors du calcul de la centralité: {str(e)}")
    
    def detect_patterns(self) -> List[Dict[str, Any]]:
        """
        Détecte des motifs suspects dans le graphe de transactions
        
        Returns:
            Liste des motifs suspects détectés
        """
        self.suspicious_patterns = []
        
        # Détecter les motifs de blanchiment courants
        self._detect_layering()
        self._detect_smurfing()
        self._detect_cycling()
        self._detect_sudden_activity()
        
        return self.suspicious_patterns
    
    def identify_exchanges(self) -> Set[str]:
        """
        Identifie les exchanges dans le graphe
        
        Returns:
            Ensemble des adresses d'exchanges identifiées
        """
        self.exchanges = set()
        
        # Identifier les exchanges connus
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("is_exchange", False):
                self.exchanges.add(node)
                
        # Identifier les potentiels exchanges non répertoriés
        # en fonction des caractéristiques typiques des exchanges
        for node in self.graph.nodes():
            if node in self.exchanges:
                continue
                
            in_degree = self.graph.in_degree(node)
            out_degree = self.graph.out_degree(node)
            
            # Les exchanges ont généralement beaucoup de connexions
            # entrantes et sortantes
            if in_degree > 10 and out_degree > 10:
                # Calculer le ratio volume/transactions
                total_volume = 0
                transaction_count = 0
                
                for _, _, data in self.graph.in_edges(node, data=True):
                    if "amount" in data:
                        total_volume += data["amount"]
                        transaction_count += 1
                    elif "transactions" in data:
                        for tx in data["transactions"]:
                            total_volume += tx.get("amount", 0)
                            transaction_count += 1
                
                # Les exchanges ont souvent des volumes élevés
                if total_volume > 10000 and transaction_count > 20:
                    self.graph.nodes[node]["potential_exchange"] = True
                    self.suspicious_patterns.append({
                        "type": "potential_exchange",
                        "address": node,
                        "confidence": 0.7,
                        "details": {
                            "in_degree": in_degree,
                            "out_degree": out_degree,
                            "volume": total_volume,
                            "transaction_count": transaction_count
                        }
                    })
        
        return self.exchanges
    
    def _detect_layering(self) -> None:
        """
        Détecte le motif de "layering" (superposition)
        où les fonds passent par une série d'adresses intermédiaires
        """
        # Chercher des chemins linéaires de longueur significative
        for node in self.graph.nodes():
            # Trouver les chemins qui partent de ce nœud
            paths = []
            self._find_linear_paths(node, [], paths, max_depth=5)
            
            # Analyser les chemins de longueur significative
            for path in [p for p in paths if len(p) >= 3]:
                # Vérifier si les montants sont similaires (indicateur de layering)
                amounts = []
                for i in range(len(path)-1):
                    source = path[i]
                    target = path[i+1]
                    
                    if self.graph.has_edge(source, target):
                        edge_data = self.graph[source][target]
                        if "amount" in edge_data:
                            amounts.append(edge_data["amount"])
                        elif "total_amount" in edge_data:
                            amounts.append(edge_data["total_amount"])
                
                if len(amounts) >= 2:
                    # Calculer l'écart-type relatif
                    std_dev = np.std(amounts)
                    mean = np.mean(amounts)
                    if mean > 0:
                        relative_std = std_dev / mean
                        
                        # Si les montants sont similaires, c'est suspect
                        if relative_std < 0.2:
                            self.suspicious_patterns.append({
                                "type": "layering",
                                "path": path,
                                "confidence": 0.8 if relative_std < 0.1 else 0.6,
                                "details": {
                                    "amounts": amounts,
                                    "relative_std": relative_std
                                }
                            })
    
    def _find_linear_paths(
        self, 
        current_node: str, 
        current_path: List[str], 
        all_paths: List[List[str]], 
        max_depth: int
    ) -> None:
        """
        Trouve récursivement des chemins linéaires dans le graphe
        
        Args:
            current_node: Nœud actuel
            current_path: Chemin courant
            all_paths: Liste pour stocker tous les chemins trouvés
            max_depth: Profondeur maximale de recherche
        """
        # Ajouter le nœud actuel au chemin
        path = current_path + [current_node]
        
        # Si on a atteint la profondeur maximale, arrêter
        if len(path) > max_depth:
            all_paths.append(path)
            return
        
        # Examiner les successeurs
        successors = list(self.graph.successors(current_node))
        
        # Si pas de successeur, c'est une feuille
        if not successors:
            all_paths.append(path)
            return
            
        # Si plusieurs successeurs, ce n'est plus un chemin linéaire
        if len(successors) > 1:
            all_paths.append(path)
            return
            
        # Continuer avec l'unique successeur
        next_node = successors[0]
        if next_node not in path:  # Éviter les cycles
            self._find_linear_paths(next_node, path, all_paths, max_depth)
        else:
            all_paths.append(path)
    
    def _detect_smurfing(self) -> None:
        """
        Détecte le motif de "smurfing" (fractionnement)
        où une somme importante est divisée en plusieurs petites transactions
        """
        for node in self.graph.nodes():
            outgoing_edges = list(self.graph.out_edges(node, data=True))
            
            if len(outgoing_edges) < 3:
                continue
                
            # Collecter les montants et timestamps
            transactions = []
            for _, target, data in outgoing_edges:
                if "amount" in data:
                    transactions.append({
                        "target": target,
                        "amount": data["amount"],
                        "timestamp": data.get("timestamp", 0)
                    })
                elif "transactions" in data:
                    for tx in data["transactions"]:
                        transactions.append({
                            "target": target,
                            "amount": tx.get("amount", 0),
                            "timestamp": tx.get("timestamp", 0)
                        })
            
            # Trier par timestamp
            transactions.sort(key=lambda x: x["timestamp"])
            
            # Vérifier si plusieurs transactions ont été effectuées dans un court laps de temps
            if len(transactions) >= 3:
                # Calculer les intervalles de temps entre transactions
                time_intervals = [
                    transactions[i+1]["timestamp"] - transactions[i]["timestamp"]
                    for i in range(len(transactions)-1)
                ]
                
                # Calculer la moyenne des montants
                amounts = [tx["amount"] for tx in transactions]
                avg_amount = np.mean(amounts)
                
                # Vérifier si les transactions sont similaires et proches dans le temps
                if max(time_intervals) < 3600 and np.std(amounts) / avg_amount < 0.3:
                    targets = [tx["target"] for tx in transactions]
                    self.suspicious_patterns.append({
                        "type": "smurfing",
                        "address": node,
                        "targets": targets,
                        "confidence": 0.7,
                        "details": {
                            "transaction_count": len(transactions),
                            "avg_amount": avg_amount,
                            "max_time_interval": max(time_intervals)
                        }
                    })
    
    def _detect_cycling(self) -> None:
        """
        Détecte les cycles dans le graphe, où les fonds reviennent à leur point d'origine
        """
        try:
            # Trouver tous les cycles simples
            cycles = list(nx.simple_cycles(self.graph))
            
            for cycle in cycles:
                if len(cycle) >= 3:  # Ignorer les cycles trop courts
                    # Vérifier les montants sur le cycle
                    amounts = []
                    timestamps = []
                    
                    for i in range(len(cycle)):
                        source = cycle[i]
                        target = cycle[(i+1) % len(cycle)]
                        
                        if self.graph.has_edge(source, target):
                            edge_data = self.graph[source][target]
                            if "amount" in edge_data:
                                amounts.append(edge_data["amount"])
                                timestamps.append(edge_data.get("timestamp", 0))
                            elif "transactions" in edge_data:
                                # Prendre la transaction la plus récente
                                latest_tx = max(edge_data["transactions"], key=lambda x: x.get("timestamp", 0))
                                amounts.append(latest_tx.get("amount", 0))
                                timestamps.append(latest_tx.get("timestamp", 0))
                    
                    # Vérifier si les montants sont similaires
                    if len(amounts) == len(cycle) and np.std(amounts) / np.mean(amounts) < 0.3:
                        # Vérifier si les transactions sont ordonnées dans le temps
                        sorted_timestamps = sorted(timestamps)
                        if timestamps == sorted_timestamps:
                            self.suspicious_patterns.append({
                                "type": "cycling",
                                "cycle": cycle,
                                "confidence": 0.9,
                                "details": {
                                    "amounts": amounts,
                                    "timestamps": timestamps
                                }
                            })
        except Exception as e:
            print(f"Erreur lors de la détection des cycles: {str(e)}")
    
    def _detect_sudden_activity(self) -> None:
        """
        Détecte une activité soudaine et anormale sur une adresse
        """
        for node, attrs in self.graph.nodes(data=True):
            # Ignorer les adresses avec peu de transactions
            if attrs.get("transaction_count", 0) < 5:
                continue
                
            # Collecter toutes les transactions (entrantes et sortantes)
            transactions = []
            
            # Transactions entrantes
            for source, _, data in self.graph.in_edges(node, data=True):
                if "timestamp" in data:
                    transactions.append({
                        "type": "in",
                        "timestamp": data["timestamp"],
                        "amount": data.get("amount", 0)
                    })
                elif "transactions" in data:
                    for tx in data["transactions"]:
                        transactions.append({
                            "type": "in",
                            "timestamp": tx.get("timestamp", 0),
                            "amount": tx.get("amount", 0)
                        })
            
            # Transactions sortantes
            for _, target, data in self.graph.out_edges(node, data=True):
                if "timestamp" in data:
                    transactions.append({
                        "type": "out",
                        "timestamp": data["timestamp"],
                        "amount": data.get("amount", 0)
                    })
                elif "transactions" in data:
                    for tx in data["transactions"]:
                        transactions.append({
                            "type": "out",
                            "timestamp": tx.get("timestamp", 0),
                            "amount": tx.get("amount", 0)
                        })
            
            # Trier par timestamp
            transactions.sort(key=lambda x: x["timestamp"])
            
            # Examiner les différences de temps
            if len(transactions) >= 5:
                timestamps = [tx["timestamp"] for tx in transactions]
                time_diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                
                # Calculer la moyenne et l'écart-type des intervalles
                mean_diff = np.mean(time_diffs)
                std_diff = np.std(time_diffs)
                
                # Identifier les groupes de transactions rapprochées
                clusters = []
                current_cluster = [transactions[0]]
                
                for i in range(1, len(transactions)):
                    prev_time = transactions[i-1]["timestamp"]
                    curr_time = transactions[i]["timestamp"]
                    
                    if curr_time - prev_time < mean_diff / 2:
                        current_cluster.append(transactions[i])
                    else:
                        if len(current_cluster) >= 3:
                            clusters.append(current_cluster)
                        current_cluster = [transactions[i]]
                
                if len(current_cluster) >= 3:
                    clusters.append(current_cluster)
                
                # Analyser les clusters pour détecter des activités suspectes
                for cluster in clusters:
                    in_volume = sum(tx["amount"] for tx in cluster if tx["type"] == "in")
                    out_volume = sum(tx["amount"] for tx in cluster if tx["type"] == "out")
                    
                    # Une activité où de l'argent entre et sort rapidement est suspecte
                    if in_volume > 0 and out_volume > 0 and min(in_volume, out_volume) / max(in_volume, out_volume) > 0.8:
                        self.suspicious_patterns.append({
                            "type": "sudden_activity",
                            "address": node,
                            "confidence": 0.75,
                            "details": {
                                "cluster_size": len(cluster),
                                "in_volume": in_volume,
                                "out_volume": out_volume,
                                "start_time": cluster[0]["timestamp"],
                                "end_time": cluster[-1]["timestamp"]
                            }
                        })
    
    def export_graph_data(self) -> Dict[str, Any]:
        """
        Exporte les données du graphe pour la visualisation avec les métriques d'analyse
        
        Returns:
            Dictionnaire formaté pour D3.js avec les résultats d'analyse
        """
        nodes = []
        links = []
        
        # Calculer la centralité max pour normaliser la taille des nœuds
        max_centrality = 0.01  # Valeur minimale pour éviter division par zéro
        for _, attrs in self.graph.nodes(data=True):
            centrality = attrs.get("centrality_score", 0)
            if centrality > max_centrality:
                max_centrality = centrality
        
        # Convertir les nœuds
        for node_id, attrs in self.graph.nodes(data=True):
            # Calculer un score pour la taille du nœud
            size_score = 5 + 45 * (attrs.get("centrality_score", 0) / max_centrality)
            
            # Déterminer la couleur du nœud
            color = "#1f77b4"  # Couleur par défaut
            if attrs.get("is_exchange", False):
                color = "#d62728"  # Rouge pour les exchanges connus
            elif attrs.get("potential_exchange", False):
                color = "#ff7f0e"  # Orange pour les exchanges potentiels
            elif attrs.get("is_start", False):
                color = "#2ca02c"  # Vert pour l'adresse de départ
            
            node_data = {
                "id": node_id,
                "label": self._format_address_label(node_id),
                "size": size_score,
                "color": color,
                **attrs
            }
            nodes.append(node_data)
        
        # Convertir les arêtes
        for source, target, attrs in self.graph.edges(data=True):
            # Calculer l'épaisseur de l'arête
            width = 1
            if "amount" in attrs:
                width = 1 + min(5, attrs["amount"] / 100)
            elif "total_amount" in attrs:
                width = 1 + min(5, attrs["total_amount"] / 100)
                
            edge_data = {
                "source": source,
                "target": target,
                "width": width,
                **attrs
            }
            links.append(edge_data)
        
        # Calculer des métriques globales
        self.metrics = {
            "node_count": len(nodes),
            "edge_count": len(links),
            "suspicious_patterns": len(self.suspicious_patterns),
            "exchanges_count": len(self.exchanges),
            "total_volume": sum(
                link.get("amount", link.get("total_amount", 0)) 
                for link in links 
                if "amount" in link or "total_amount" in link
            )
        }
        
        return {
            "nodes": nodes,
            "links": links,
            "metrics": self.metrics,
            "suspicious_patterns": self.suspicious_patterns
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
            
        # Format: "kaspa:qz...at" (les 8 premiers et 4 derniers caractères)
        if len(address) > 15:
            return f"{address[:10]}...{address[-4:]}"
        return address