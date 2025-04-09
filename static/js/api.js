/**
 * Module pour la communication avec l'API du serveur
 */
class KaspaAPI {
    /**
     * Initialise le client API
     */
    constructor() {
        this.baseUrl = '/api';
    }

    /**
     * Analyse les transactions à partir d'une adresse
     * 
     * @param {Object} params - Paramètres de l'analyse
     * @param {string} params.startAddress - Adresse Kaspa de départ
     * @param {number} params.depth - Profondeur de l'analyse
     * @param {number} params.minAmount - Montant minimum à considérer
     * @param {number} params.maxTransactions - Nombre maximum de transactions
     * @param {boolean} params.includeExchanges - Activer la détection d'exchanges
     * @returns {Promise<Object>} - Données du graphe
     */
    async analyzeTransactions(params) {
        try {
            const response = await fetch(`${this.baseUrl}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    start_address: params.startAddress,
                    depth: params.depth,
                    min_amount: params.minAmount,
                    max_transactions: params.maxTransactions,
                    include_exchanges: params.includeExchanges
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Erreur lors de l\'analyse des transactions');
            }

            return await response.json();
        } catch (error) {
            console.error('Erreur API:', error);
            throw error;
        }
    }

    /**
     * Récupère les informations détaillées sur une adresse
     * 
     * @param {string} address - Adresse Kaspa
     * @returns {Promise<Object>} - Informations sur l'adresse
     */
    async getAddressInfo(address) {
        try {
            const response = await fetch(`${this.baseUrl}/address/${address}`);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Erreur lors de la récupération des informations');
            }

            return await response.json();
        } catch (error) {
            console.error('Erreur API:', error);
            throw error;
        }
    }
}

// Exporte une instance unique
const kaspaAPI = new KaspaAPI();
