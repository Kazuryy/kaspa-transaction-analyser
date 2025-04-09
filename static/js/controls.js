/**
 * Module de gestion des contrôles de l'interface utilisateur
 * Gère les interactions avec les formulaires, boutons et filtres
 */
document.addEventListener('DOMContentLoaded', () => {
    // Références aux éléments du DOM
    const analysisForm = document.getElementById('analysis-form');
    const startAddressInput = document.getElementById('start-address');
    const depthSelect = document.getElementById('depth');
    const minAmountInput = document.getElementById('min-amount');
    const maxTxsInput = document.getElementById('max-txs');
    const includeExchangesCheckbox = document.getElementById('include-exchanges');
    const analyzeBtn = document.getElementById('analyze-btn');
    const spinner = document.getElementById('spinner');
    const loadingOverlay = document.getElementById('loading-overlay');
    const graphPlaceholder = document.getElementById('graph-placeholder');
    
    // Filtres
    const nodeFilterInput = document.getElementById('node-filter');
    const filterExchangesCheckbox = document.getElementById('filter-exchanges');
    const filterSuspiciousCheckbox = document.getElementById('filter-suspicious');
    const showLabelsCheckbox = document.getElementById('show-labels');
    
    // Boutons de zoom et vue
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const resetViewBtn = document.getElementById('reset-view-btn');
    const exportBtn = document.getElementById('export-btn');
    
    // Boutons de layout
    const layoutForceBtn = document.getElementById('layout-force');
    const layoutRadialBtn = document.getElementById('layout-radial');
    const layoutTreeBtn = document.getElementById('layout-tree');
    
    // Métriques
    const metricsLoading = document.getElementById('metrics-loading');
    const metricsContent = document.getElementById('metrics-content');
    const nodeCountElem = document.getElementById('node-count');
    const edgeCountElem = document.getElementById('edge-count');
    const totalVolumeElem = document.getElementById('total-volume');
    const suspiciousCountElem = document.getElementById('suspicious-count');
    const exchangesCountElem = document.getElementById('exchanges-count');
    
    // Alertes
    const alertsPlaceholder = document.getElementById('alerts-placeholder');
    const alertsList = document.getElementById('alerts-list');
    
    // Gestionnaire de soumission du formulaire d'analyse
    analysisForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        // Récupérer les valeurs du formulaire
        const startAddress = startAddressInput.value.trim();
        const depth = parseInt(depthSelect.value);
        const minAmount = parseFloat(minAmountInput.value);
        const maxTransactions = parseInt(maxTxsInput.value);
        const includeExchanges = includeExchangesCheckbox.checked;
        
        // Validation basique
        if (!startAddress) {
            alert('Veuillez entrer une adresse Kaspa valide');
            return;
        }
        
        // Afficher l'état de chargement
        showLoading(true);
        
        try {
            // Appeler l'API pour analyser les transactions
            const graphData = await kaspaAPI.analyzeTransactions({
                startAddress,
                depth,
                minAmount,
                maxTransactions,
                includeExchanges
            });
            
            // Masquer le placeholder et afficher le graphe
            graphPlaceholder.classList.add('d-none');
            
            // Visualiser les données
            graphVisualizer.visualize(graphData);
            
            // Mettre à jour les métriques
            updateMetrics(graphData.metrics);
            
            // Afficher les patterns suspects
            displaySuspiciousPatterns(graphData.suspicious_patterns || []);
            
        } catch (error) {
            console.error('Erreur lors de l\'analyse:', error);
            alert(`Erreur: ${error.message || 'Impossible d\'analyser les transactions'}`);
        } finally {
            // Masquer l'état de chargement
            showLoading(false);
        }
    });
    
    // Filtrage des nœuds par texte
    nodeFilterInput.addEventListener('input', () => {
        graphVisualizer.filterNodes(nodeFilterInput.value.trim());
    });
    
    // Filtres d'affichage
    filterExchangesCheckbox.addEventListener('change', () => {
        graphVisualizer.updateExchangesVisibility(filterExchangesCheckbox.checked);
    });
    
    filterSuspiciousCheckbox.addEventListener('change', () => {
        graphVisualizer.updateSuspiciousVisibility(filterSuspiciousCheckbox.checked);
    });
    
    showLabelsCheckbox.addEventListener('change', () => {
        graphVisualizer.updateLabelsVisibility(showLabelsCheckbox.checked);
    });
    
    // Contrôles de zoom
    zoomInBtn.addEventListener('click', () => {
        const svg = d3.select('#graph-svg');
        const currentTransform = d3.zoomTransform(svg.node());
        
        svg.transition()
            .duration(300)
            .call(graphVisualizer.zoom.transform, 
                  d3.zoomIdentity.translate(currentTransform.x, currentTransform.y).scale(currentTransform.k * 1.3));
    });
    
    zoomOutBtn.addEventListener('click', () => {
        const svg = d3.select('#graph-svg');
        const currentTransform = d3.zoomTransform(svg.node());
        
        svg.transition()
            .duration(300)
            .call(graphVisualizer.zoom.transform, 
                  d3.zoomIdentity.translate(currentTransform.x, currentTransform.y).scale(currentTransform.k / 1.3));
    });
    
    resetViewBtn.addEventListener('click', () => {
        graphVisualizer.centerView();
    });
    
    exportBtn.addEventListener('click', () => {
        graphVisualizer.exportAsSVG();
    });
    
    // Contrôles de layout
    layoutForceBtn.addEventListener('click', () => {
        updateLayoutButtons('force');
        graphVisualizer.useForceLayout();
    });
    
    layoutRadialBtn.addEventListener('click', () => {
        updateLayoutButtons('radial');
        graphVisualizer.useRadialLayout();
    });
    
    layoutTreeBtn.addEventListener('click', () => {
        updateLayoutButtons('tree');
        graphVisualizer.useTreeLayout();
    });
    
    /**
     * Affiche ou masque l'indicateur de chargement
     */
    function showLoading(show) {
        if (show) {
            spinner.classList.remove('d-none');
            loadingOverlay.classList.remove('d-none');
            analyzeBtn.disabled = true;
        } else {
            spinner.classList.add('d-none');
            loadingOverlay.classList.add('d-none');
            analyzeBtn.disabled = false;
        }
    }
    
    /**
     * Met à jour les métriques affichées
     */
    function updateMetrics(metrics) {
        if (!metrics) return;
        
        metricsLoading.classList.add('d-none');
        metricsContent.classList.remove('d-none');
        
        nodeCountElem.textContent = metrics.node_count || 0;
        edgeCountElem.textContent = metrics.edge_count || 0;
        totalVolumeElem.textContent = `${formatNumber(metrics.total_volume || 0)} KAS`;
        suspiciousCountElem.textContent = metrics.suspicious_patterns || 0;
        exchangesCountElem.textContent = metrics.exchanges_count || 0;
    }
    
    /**
     * Affiche les patterns suspects détectés
     */
    function displaySuspiciousPatterns(patterns) {
        alertsList.innerHTML = '';
        
        if (!patterns || patterns.length === 0) {
            alertsPlaceholder.classList.remove('d-none');
            alertsList.classList.add('d-none');
            return;
        }
        
        alertsPlaceholder.classList.add('d-none');
        alertsList.classList.remove('d-none');
        
        // Trier les patterns par confiance décroissante
        patterns.sort((a, b) => b.confidence - a.confidence);
        
        // Créer un élément pour chaque pattern
        patterns.forEach(pattern => {
            const patternElem = document.createElement('div');
            patternElem.className = `alert-pattern ${pattern.type}`;
            
            // Formater le titre selon le type de pattern
            let title = '';
            let description = '';
            
            switch (pattern.type) {
                case 'layering':
                    title = 'Superposition (Layering)';
                    description = `Chaîne de ${pattern.path.length} transactions avec des montants similaires`;
                    break;
                case 'smurfing':
                    title = 'Fractionnement (Smurfing)';
                    description = `${pattern.details.transaction_count} transactions de montant moyen ${formatNumber(pattern.details.avg_amount)} KAS`;
                    break;
                case 'cycling':
                    title = 'Cycle de transactions';
                    description = `Cycle de ${pattern.cycle.length} adresses où les fonds reviennent à l'origine`;
                    break;
                case 'sudden_activity':
                    title = 'Activité soudaine';
                    description = `Cluster de ${pattern.details.cluster_size} transactions rapprochées`;
                    break;
                case 'potential_exchange':
                    title = 'Exchange potentiel';
                    description = `Forte activité: ${pattern.details.transaction_count} transactions, volume: ${formatNumber(pattern.details.volume)} KAS`;
                    break;
                default:
                    title = 'Pattern suspect';
                    description = 'Activité inhabituelle détectée';
            }
            
            // Calculer la largeur de la barre de confiance
            const confidenceWidth = pattern.confidence * 100;
            
            // Créer le contenu HTML
            patternElem.innerHTML = `
                <h6>
                    ${title}
                    <span class="badge bg-${getConfidenceBadgeColor(pattern.confidence)}">
                        ${Math.round(pattern.confidence * 100)}% de confiance
                    </span>
                </h6>
                <p class="mb-1">${description}</p>
                <div class="address mb-2">
                    ${pattern.address || (pattern.path ? formatAddressList(pattern.path) : 
                      (pattern.cycle ? formatAddressList(pattern.cycle) : ''))}
                </div>
                <div class="progress" style="height: 6px;">
                    <div class="progress-bar bg-${getConfidenceBadgeColor(pattern.confidence)}" 
                         role="progressbar" 
                         style="width: ${confidenceWidth}%" 
                         aria-valuenow="${confidenceWidth}" 
                         aria-valuemin="0" 
                         aria-valuemax="100"></div>
                </div>
            `;
            
            // Ajouter l'élément au conteneur
            alertsList.appendChild(patternElem);
            
            // Ajouter un gestionnaire d'événement pour la mise en évidence
            patternElem.addEventListener('mouseenter', () => {
                highlightPatternNodes(pattern);
            });
            
            patternElem.addEventListener('mouseleave', () => {
                resetHighlightedNodes();
            });
        });
    }
    
    /**
     * Met en évidence les nœuds impliqués dans un pattern
     */
    function highlightPatternNodes(pattern) {
        // Récupérer toutes les adresses impliquées
        const addresses = new Set();
        
        if (pattern.address) {
            addresses.add(pattern.address);
        }
        
        if (pattern.targets) {
            pattern.targets.forEach(addr => addresses.add(addr));
        }
        
        if (pattern.path) {
            pattern.path.forEach(addr => addresses.add(addr));
        }
        
        if (pattern.cycle) {
            pattern.cycle.forEach(addr => addresses.add(addr));
        }
        
        // Mettre en évidence les nœuds
        d3.selectAll('.node')
            .style('opacity', d => addresses.has(d.id) ? 1 : 0.2);
            
        d3.selectAll('.node-label')
            .style('opacity', d => addresses.has(d.id) ? 1 : 0.2);
            
        // Mettre en évidence les liens entre ces nœuds
        d3.selectAll('.link')
            .style('opacity', d => {
                const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
                const targetId = typeof d.target === 'object' ? d.target.id : d.target;
                return addresses.has(sourceId) && addresses.has(targetId) ? 0.8 : 0.1;
            });
    }
    
    /**
     * Réinitialise la mise en évidence des nœuds
     */
    function resetHighlightedNodes() {
        d3.selectAll('.node').style('opacity', 1);
        d3.selectAll('.node-label').style('opacity', 1);
        d3.selectAll('.link').style('opacity', 0.6);
    }
    
    /**
     * Met à jour l'apparence des boutons de layout
     */
    function updateLayoutButtons(activeLayout) {
        layoutForceBtn.classList.toggle('btn-outline-light', activeLayout !== 'force');
        layoutForceBtn.classList.toggle('btn-light', activeLayout === 'force');
        
        layoutRadialBtn.classList.toggle('btn-outline-light', activeLayout !== 'radial');
        layoutRadialBtn.classList.toggle('btn-light', activeLayout === 'radial');
        
        layoutTreeBtn.classList.toggle('btn-outline-light', activeLayout !== 'tree');
        layoutTreeBtn.classList.toggle('btn-light', activeLayout === 'tree');
    }
    
    /**
     * Formate une liste d'adresses pour l'affichage
     */
    function formatAddressList(addresses) {
        if (!addresses || addresses.length === 0) return '';
        
        if (addresses.length === 1) {
            return addresses[0];
        }
        
        if (addresses.length === 2) {
            return `${formatShortAddress(addresses[0])} → ${formatShortAddress(addresses[1])}`;
        }
        
        return `${formatShortAddress(addresses[0])} → ... → ${formatShortAddress(addresses[addresses.length-1])} (${addresses.length} adresses)`;
    }
    
    /**
     * Formate une adresse courte
     */
    function formatShortAddress(address) {
        if (!address) return '';
        if (address.length <= 15) return address;
        return `${address.substring(0, 10)}...${address.substring(address.length - 4)}`;
    }
    
    /**
     * Détermine la couleur du badge en fonction du niveau de confiance
     */
    function getConfidenceBadgeColor(confidence) {
        if (confidence >= 0.8) return 'danger';
        if (confidence >= 0.6) return 'warning';
        return 'secondary';
    }
    
    /**
     * Formate un nombre pour l'affichage
     */
    function formatNumber(num) {
        return parseFloat(num).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
});
