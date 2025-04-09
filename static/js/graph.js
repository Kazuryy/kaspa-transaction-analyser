/**
 * Module de visualisation du graphe de transactions
 * Utilise D3.js pour créer une visualisation interactive
 */
class GraphVisualizer {
    /**
     * Initialise le visualiseur de graphe
     * 
     * @param {string} svgId - ID de l'élément SVG pour le rendu
     * @param {string} tooltipId - ID de l'élément tooltip
     */
    constructor(svgId = 'graph-svg', tooltipId = 'tooltip') {
        this.svg = d3.select(`#${svgId}`);
        this.tooltip = d3.select(`#${tooltipId}`);
        this.width = this.svg.node().clientWidth;
        this.height = this.svg.node().clientHeight;
        
        // Groupe pour les liens (arêtes)
        this.linkGroup = this.svg.append('g').attr('class', 'links');
        
        // Groupe pour les nœuds
        this.nodeGroup = this.svg.append('g').attr('class', 'nodes');
        
        // Groupe pour les labels des nœuds
        this.labelGroup = this.svg.append('g').attr('class', 'labels');
        
        // Système de zoom
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 8])
            .on('zoom', event => {
                this.linkGroup.attr('transform', event.transform);
                this.nodeGroup.attr('transform', event.transform);
                this.labelGroup.attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);
        
        // Simulation de forces pour le layout
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(d => (d.size || 10) + 5));
        
        // État
        this.nodes = [];
        this.links = [];
        this.selectedNode = null;
        this.currentLayout = 'force';
        
        // Options d'affichage
        this.showLabels = true;
        this.highlightSuspicious = true;
        this.showExchanges = true;
        
        // Gestion du redimensionnement
        window.addEventListener('resize', this.resize.bind(this));
    }

    /**
     * Gère le redimensionnement de la fenêtre
     */
    resize() {
        this.width = this.svg.node().clientWidth;
        this.height = this.svg.node().clientHeight;
        
        if (this.simulation) {
            this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
            this.simulation.alpha(0.3).restart();
        }
    }

    /**
     * Visualise les données du graphe
     * 
     * @param {Object} graphData - Données du graphe (nœuds et liens)
     */
    visualize(graphData) {
        console.log("Données de graphe reçues:", graphData);
        
        // Stocker les données
        this.nodes = graphData.nodes || [];
        this.links = graphData.links || [];
        this.suspiciousPatterns = graphData.suspicious_patterns || [];
        
        // Nettoyer le graphe existant
        this.clear();
        
        // Vérifier si nous avons des données
        if (this.nodes.length === 0) {
            console.warn("Aucun nœud à afficher");
            return;
        }
        
        // Créer la visualisation
        this.createLinks();
        this.createNodes();
        this.createLabels();
        
        // Démarrer la simulation
        this.simulation.nodes(this.nodes);
        this.simulation.force('link').links(this.links);
        this.simulation.alpha(1).restart();
        
        // Centrer la vue
        this.centerView();
    }

    /**
     * Nettoie le graphe existant
     */
    clear() {
        this.linkGroup.selectAll('*').remove();
        this.nodeGroup.selectAll('*').remove();
        this.labelGroup.selectAll('*').remove();
        
        if (this.simulation) {
            this.simulation.stop();
        }
    }

    /**
     * Crée les liens (arêtes) du graphe
     */
    createLinks() {
        // Définir les marqueurs de flèche
        const defs = this.svg.append('defs');
        
        defs.append('marker')
            .attr('id', 'arrow')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 25)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#666');
            
        // Créer les arêtes
        this.linkElements = this.linkGroup.selectAll('path')
            .data(this.links)
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('stroke-width', d => d.width || 1)
            .attr('marker-end', 'url(#arrow)');
        
        // Mettre à jour les positions des liens lors de la simulation
        this.simulation.on('tick', () => this.tick());
    }

    /**
     * Crée les nœuds du graphe
     */
    createNodes() {
        this.nodeElements = this.nodeGroup.selectAll('circle')
            .data(this.nodes)
            .enter()
            .append('circle')
            .attr('class', d => {
                let classes = ['node'];
                if (d.is_start) classes.push('start');
                if (d.is_exchange) classes.push('exchange');
                if (d.potential_exchange) classes.push('potential-exchange');
                return classes.join(' ');
            })
            .attr('r', d => d.size ? Math.sqrt(d.size) * 2 : 8)
            .attr('fill', d => d.color || '#1f77b4')
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip())
            .on('click', (event, d) => this.selectNode(event, d))
            .call(d3.drag()
                .on('start', (event, d) => this.dragStart(event, d))
                .on('drag', (event, d) => this.drag(event, d))
                .on('end', (event, d) => this.dragEnd(event, d))
            );
    }

    /**
     * Crée les étiquettes des nœuds
     */
    createLabels() {
        this.labelElements = this.labelGroup.selectAll('text')
            .data(this.nodes)
            .enter()
            .append('text')
            .attr('class', 'node-label')
            .text(d => d.label || d.id)
            .attr('font-size', d => d.is_start ? '12px' : '10px')
            .attr('dx', 0)
            .attr('dy', d => -((d.size ? Math.sqrt(d.size) * 2 : 8) + 8));
        
        // Mettre à jour la visibilité initiale
        this.updateLabelsVisibility();
    }

    /**
     * Mise à jour des positions lors de chaque tick de la simulation
     */
    tick() {
        // Mettre à jour les positions des nœuds
        this.nodeElements
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        
        // Mettre à jour les positions des liens
        this.linkElements
            .attr('d', d => {
                // S'assurer que source et target sont des objets avec x et y
                const sourceNode = typeof d.source === 'object' ? d.source : this.nodes.find(n => n.id === d.source);
                const targetNode = typeof d.target === 'object' ? d.target : this.nodes.find(n => n.id === d.target);
                
                if (!sourceNode || !targetNode) {
                    console.error("Nœud source ou cible non trouvé pour:", d);
                    return "M0,0L0,0"; // Ligne vide
                }
                
                const sourceRadius = sourceNode.size ? Math.sqrt(sourceNode.size) * 2 : 8;
                const targetRadius = targetNode.size ? Math.sqrt(targetNode.size) * 2 : 8;
                
                const start = this.getPointOnCircle(sourceNode.x, sourceNode.y, sourceRadius, targetNode.x, targetNode.y);
                const end = this.getPointOnCircle(targetNode.x, targetNode.y, targetRadius, sourceNode.x, sourceNode.y);
                
                return `M${start.x},${start.y}L${end.x},${end.y}`;
            });
        
        // Mettre à jour les positions des labels
        this.labelElements
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    }

    /**
     * Calcule un point sur le cercle d'un nœud dans la direction d'un autre point
     */
    getPointOnCircle(cx, cy, r, tx, ty) {
        const dx = tx - cx;
        const dy = ty - cy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        if (dist === 0) return { x: cx, y: cy }; // Éviter la division par zéro
        
        return {
            x: cx + (dx * r) / dist,
            y: cy + (dy * r) / dist
        };
    }

    /**
     * Gère le début du glisser-déposer d'un nœud
     */
    dragStart(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    /**
     * Gère le glisser-déposer d'un nœud
     */
    drag(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    /**
     * Gère la fin du glisser-déposer d'un nœud
     */
    dragEnd(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        
        // Si le nœud n'est pas fixe, libérer sa position
        if (!d.fixed) {
            d.fx = null;
            d.fy = null;
        }
    }

    /**
     * Affiche la tooltip pour un nœud
     */
    showTooltip(event, d) {
        // Mettre en évidence le nœud
        d3.select(event.currentTarget).classed('highlighted', true);
        
        // Mettre en évidence les liens connectés
        this.highlightConnectedLinks(d.id);
        
        // Formater le contenu de la tooltip
        let content = `
            <h6>${d.label || d.id}</h6>
            <div class="tooltip-field">
                <span class="tooltip-label">Balance:</span>
                <span class="tooltip-value">${this.formatAmount(d.balance)} KAS</span>
            </div>
            <div class="tooltip-field">
                <span class="tooltip-label">Reçu:</span>
                <span class="tooltip-value">${this.formatAmount(d.total_received)} KAS</span>
            </div>
            <div class="tooltip-field">
                <span class="tooltip-label">Envoyé:</span>
                <span class="tooltip-value">${this.formatAmount(d.total_sent)} KAS</span>
            </div>
            <div class="tooltip-field">
                <span class="tooltip-label">Transactions:</span>
                <span class="tooltip-value">${d.transaction_count || 0}</span>
            </div>
        `;
        
        // Ajouter des informations supplémentaires
        if (d.is_exchange) {
            content += `<div class="tooltip-field">
                <span class="tooltip-label">Type:</span>
                <span class="tooltip-value">Exchange connu</span>
            </div>`;
        } else if (d.potential_exchange) {
            content += `<div class="tooltip-field">
                <span class="tooltip-label">Type:</span>
                <span class="tooltip-value">Exchange potentiel</span>
            </div>`;
        } else if (d.is_start) {
            content += `<div class="tooltip-field">
                <span class="tooltip-label">Type:</span>
                <span class="tooltip-value">Adresse de départ</span>
            </div>`;
        }
        
        // Afficher la tooltip
        this.tooltip
            .html(content)
            .style('display', 'block')
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
    }

    /**
     * Masque la tooltip
     */
    hideTooltip() {
        // Retirer la mise en évidence
        this.nodeElements.classed('highlighted', false);
        this.linkElements.classed('highlighted', false);
        
        // Masquer la tooltip
        this.tooltip.style('display', 'none');
    }

    /**
     * Met en évidence les liens connectés à un nœud
     */
    highlightConnectedLinks(nodeId) {
        this.linkElements.classed('highlighted', d => {
            const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
            const targetId = typeof d.target === 'object' ? d.target.id : d.target;
            return sourceId === nodeId || targetId === nodeId;
        });
    }

    /**
     * Sélectionne un nœud pour le visualiser en détail
     */
    selectNode(event, d) {
        // Désélectionner le nœud précédent
        if (this.selectedNode) {
            this.nodeElements
                .filter(node => node.id === this.selectedNode)
                .classed('selected', false);
        }
        
        // Sélectionner le nouveau nœud
        const isSelected = d.id === this.selectedNode;
        this.selectedNode = isSelected ? null : d.id;
        
        // Mettre à jour la classe CSS
        d3.select(event.currentTarget).classed('selected', !isSelected);
        
        // Déclencher un événement pour notifier la sélection
        const selectEvent = new CustomEvent('nodeSelected', {
            detail: { node: isSelected ? null : d }
        });
        document.dispatchEvent(selectEvent);
    }

    /**
     * Filtre les nœuds par recherche textuelle
     */
    filterNodes(searchText) {
        if (!searchText) {
            // Réinitialiser tous les nœuds
            this.nodeElements.style('opacity', 1);
            this.linkElements.style('opacity', 0.6);
            this.labelElements.style('opacity', 1);
            return;
        }
        
        // Convertir en minuscules pour la recherche
        const search = searchText.toLowerCase();
        
        // Filtrer les nœuds
        this.nodeElements.style('opacity', d => {
            const matchesId = d.id && d.id.toLowerCase().includes(search);
            const matchesLabel = d.label && d.label.toLowerCase().includes(search);
            return (matchesId || matchesLabel) ? 1 : 0.1;
        });
        
        // Filtrer les liens
        this.linkElements.style('opacity', d => {
            const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
            const targetId = typeof d.target === 'object' ? d.target.id : d.target;
            
            const sourceMatches = sourceId && sourceId.toLowerCase().includes(search);
            const targetMatches = targetId && targetId.toLowerCase().includes(search);
            
            return (sourceMatches || targetMatches) ? 0.6 : 0.1;
        });
        
        // Filtrer les labels
        this.labelElements.style('opacity', d => {
            const matchesId = d.id && d.id.toLowerCase().includes(search);
            const matchesLabel = d.label && d.label.toLowerCase().includes(search);
            return (matchesId || matchesLabel) ? 1 : 0.1;
        });
    }

    /**
     * Met à jour l'affichage des exchanges
     */
    updateExchangesVisibility(show) {
        this.showExchanges = show;
        
        this.nodeElements
            .filter(d => d.is_exchange || d.potential_exchange)
            .style('opacity', show ? 1 : 0.2);
            
        this.labelElements
            .filter(d => d.is_exchange || d.potential_exchange)
            .style('opacity', show ? 1 : 0.2);
            
        // Filtrer également les liens connectés
        this.linkElements.style('opacity', d => {
            const isExchangeLink = (
                (typeof d.source === 'object' && (d.source.is_exchange || d.source.potential_exchange)) ||
                (typeof d.target === 'object' && (d.target.is_exchange || d.target.potential_exchange))
            );
            return isExchangeLink && !show ? 0.1 : 0.6;
        });
    }

    /**
     * Met à jour l'affichage des adresses suspectes
     */
    updateSuspiciousVisibility(highlight) {
        this.highlightSuspicious = highlight;
        
        // Trouver toutes les adresses impliquées dans des patterns suspects
        const suspiciousAddresses = new Set();
        
        if (this.suspiciousPatterns && this.suspiciousPatterns.length > 0) {
            this.suspiciousPatterns.forEach(pattern => {
                if (pattern.address) {
                    suspiciousAddresses.add(pattern.address);
                }
                if (pattern.path) {
                    pattern.path.forEach(addr => suspiciousAddresses.add(addr));
                }
                if (pattern.cycle) {
                    pattern.cycle.forEach(addr => suspiciousAddresses.add(addr));
                }
                if (pattern.targets) {
                    pattern.targets.forEach(addr => suspiciousAddresses.add(addr));
                }
            });
        }
        
        // Mettre à jour l'apparence des nœuds
        this.nodeElements.each(function(d) {
            if (!d || !d.id) return;
            
            const isSuspicious = suspiciousAddresses.has(d.id);
            if (isSuspicious && highlight) {
                d3.select(this).style('fill', '#9467bd');
            } else {
                d3.select(this).style('fill', d.color || '#1f77b4');
            }
        });
    }

    /**
     * Met à jour l'affichage des libellés de nœuds
     */
    updateLabelsVisibility(show) {
        if (show !== undefined) {
            this.showLabels = show;
        }
        
        this.labelElements.style('display', this.showLabels ? 'block' : 'none');
    }

    /**
     * Centre la vue sur le graphe
     */
    centerView() {
        const transform = d3.zoomIdentity
            .translate(this.width / 2, this.height / 2)
            .scale(0.8);
        
        this.svg.transition()
            .duration(500)
            .call(this.zoom.transform, transform);
    }

    /**
     * Utilise un layout radial pour le graphe
     */
    useRadialLayout() {
        this.currentLayout = 'radial';
        
        if (!this.nodes || this.nodes.length === 0) {
            console.warn("Pas de nœuds à organiser");
            return;
        }
        
        // Trouver le nœud de départ
        const startNode = this.nodes.find(node => node.is_start);
        const startId = startNode ? startNode.id : this.nodes[0].id;
        
        // Arrêter la simulation actuelle
        this.simulation.stop();
        
        // Calculer les niveaux pour chaque nœud
        const levels = {};
        levels[startId] = 0;
        
        const queue = [startId];
        const visited = new Set([startId]);
        
        while (queue.length > 0) {
            const current = queue.shift();
            const currentLevel = levels[current];
            
            // Trouver les voisins
            this.links.forEach(link => {
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                
                if (sourceId === current) {
                    if (!visited.has(targetId)) {
                        levels[targetId] = currentLevel + 1;
                        visited.add(targetId);
                        queue.push(targetId);
                    }
                }
            });
        }
        
        // Configurer une nouvelle simulation avec des forces radiales
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link', d3.forceLink(this.links).id(d => d.id).distance(70))
            .force('charge', d3.forceManyBody().strength(-200))
            .force('collision', d3.forceCollide().radius(d => (d.size || 10) + 5))
            .force('radial', d3.forceRadial(d => {
                const level = levels[d.id] || 0;
                return 80 + level * 100;
            }, this.width / 2, this.height / 2));
        
        // Mettre à jour les événements de tick
        this.simulation.on('tick', () => this.tick());
        
        // Lancer la simulation
        this.simulation.alpha(1).restart();
    }

    /**
     * Utilise un layout d'arbre pour le graphe
     */
    useTreeLayout() {
        this.currentLayout = 'tree';
        
        if (!this.nodes || this.nodes.length === 0) {
            console.warn("Pas de nœuds à organiser");
            return;
        }
        
        // Trouver le nœud de départ
        const startNode = this.nodes.find(node => node.is_start);
        const startId = startNode ? startNode.id : this.nodes[0].id;
        
        // Arrêter la simulation actuelle
        this.simulation.stop();
        
        // Convertir le graphe en hiérarchie
        const hierarchy = this.convertToHierarchy(startId);
        
        if (!hierarchy) {
            console.warn("Impossible de créer une hiérarchie à partir du graphe");
            this.useForceLayout();
            return;
        }
        
        try {
            // Créer un layout d'arbre
            const treeLayout = d3.tree()
                .size([this.width - 100, this.height - 100]);
            
            // Appliquer le layout
            const treeData = treeLayout(hierarchy);
            
            // Mise à jour des positions de nœuds
            treeData.descendants().forEach(d => {
                const node = this.nodes.find(n => n.id === d.data.id);
                if (node) {
                    node.x = d.x + 50;
                    node.y = d.y + 50;
                    node.fx = node.x;
                    node.fy = node.y;
                }
            });
            
            // Mise à jour du graphe
            this.tick();
            
            // Relancer une simulation minimale pour gérer les interactions
            this.simulation = d3.forceSimulation(this.nodes)
                .force('link', d3.forceLink(this.links).id(d => d.id).distance(0).strength(0))
                .force('charge', d3.forceManyBody().strength(0))
                .force('center', d3.forceCenter(0, 0).strength(0))
                .force('collision', d3.forceCollide().radius(d => (d.size || 10) + 2).strength(0.2));
                
            // Mettre à jour les événements de tick
            this.simulation.on('tick', () => this.tick());
            this.simulation.alpha(0.1).restart();
        } catch (e) {
            console.error("Erreur lors de l'application du layout d'arbre:", e);
            // Revenir au layout de force en cas d'erreur
            this.useForceLayout();
        }
    }

    /**
     * Convertit le graphe en hiérarchie pour le layout d'arbre
     */
    convertToHierarchy(rootId) {
        try {
            // Créer une structure qui représente l'arbre
            const tree = {};
            const visited = new Set();
            
            // Initialiser tous les nœuds
            this.nodes.forEach(node => {
                if (node && node.id) {
                    tree[node.id] = { id: node.id, children: [] };
                }
            });
            
            if (!rootId || !tree[rootId]) {
                console.warn("Nœud racine non trouvé:", rootId);
                return null;
            }
            
            // Fonction récursive pour construire l'arbre
            const buildTree = (nodeId, parentId = null) => {
                if (visited.has(nodeId)) return;
                visited.add(nodeId);
                
                // Trouver tous les nœuds connectés
                this.links.forEach(link => {
                    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                    
                    if (sourceId === nodeId && targetId !== parentId) {
                        if (tree[targetId]) {  // Vérifier que le nœud cible existe
                            tree[nodeId].children.push(tree[targetId]);
                            buildTree(targetId, nodeId);
                        }
                    }
                });
            };
            
            // Construire l'arbre à partir de la racine
            buildTree(rootId);
            
            // Retourner la hiérarchie D3
            return d3.hierarchy(tree[rootId]);
        } catch (e) {
            console.error("Erreur lors de la conversion en hiérarchie:", e);
            return null;
        }
    }

    /**
     * Utilise un layout de force standard
     */
    useForceLayout() {
        this.currentLayout = 'force';
        
        // Libérer les positions fixes
        this.nodes.forEach(node => {
            if (node && !node.fixed) {
                node.fx = null;
                node.fy = null;
            }
        });
        
        // Configurer une nouvelle simulation avec des forces standard
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link', d3.forceLink(this.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(d => (d.size || 10) + 5));
        
        // Mettre à jour les événements de tick
        this.simulation.on('tick', () => this.tick());
        
        // Lancer la simulation
        this.simulation.alpha(1).restart();
    }

    /**
     * Exporte le graphe actuel sous forme d'image SVG
     */
    exportAsSVG() {
        try {
            // Créer une copie du SVG
            const svgCopy = this.svg.node().cloneNode(true);
            
            // Nettoyer les attributs de style
            svgCopy.setAttribute('width', this.width);
            svgCopy.setAttribute('height', this.height);
            svgCopy.setAttribute('style', 'background-color: #222;');
            
            // Convertir en chaîne SVG
            const serializer = new XMLSerializer();
            let svgString = serializer.serializeToString(svgCopy);
            
            // Ajouter la feuille de style
            svgString = svgString.replace('<svg', 
                `<svg xmlns="http://www.w3.org/2000/svg" version="1.1"`);
            
            // Créer un Blob pour le téléchargement
            const blob = new Blob([svgString], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);
            
            // Créer un lien de téléchargement
            const downloadLink = document.createElement('a');
            downloadLink.href = url;
            downloadLink.download = 'kaspa-transaction-graph.svg';
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            
            // Libérer l'URL
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error("Erreur lors de l'exportation SVG:", e);
            alert("Erreur lors de l'exportation du graphe.");
        }
    }

    /**
     * Formate un montant pour l'affichage
     */
    formatAmount(amount) {
        if (amount === undefined || amount === null) return '0';
        return parseFloat(amount).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
}

// Créer une instance du visualiseur
const graphVisualizer = new GraphVisualizer();

// Journalisation pour debug
console.log("Module GraphVisualizer chargé");