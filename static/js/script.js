document.addEventListener('DOMContentLoaded', function() {
    // Fonction de logging qui envoie uniquement au terminal
    function logToConsole(message, type = 'info') {
        // Les logs sont maintenant uniquement envoyés au terminal
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
    
    // Log initial message
    logToConsole('Application initialized', 'info');
    
    // Accordion functionality
    const accordionHeader = document.querySelector('.accordion-header');
    const accordionContent = document.querySelector('.accordion-content');
    
    accordionHeader.addEventListener('click', function() {
        const icon = this.querySelector('i');
        
        if (accordionContent.style.display === 'none' || !accordionContent.style.display) {
            accordionContent.style.display = 'block';
            icon.className = 'fas fa-chevron-up';
            logToConsole('Options avancées ouvertes');
        } else {
            accordionContent.style.display = 'none';
            icon.className = 'fas fa-chevron-down';
            logToConsole('Options avancées fermées');
        }
    });
    
    // Initially hide accordion content
    accordionContent.style.display = 'none';
    
    // Filter tags functionality
    const activeFilters = document.getElementById('activeFilters');
    
    activeFilters.addEventListener('click', function(e) {
        if (e.target.tagName === 'I') {
            const filterTag = e.target.parentElement;
            filterTag.remove();
            logToConsole(`Filtre supprimé: ${filterTag.dataset.value}`);
        }
    });
    
    // Save filter button
    const saveFilterBtn = document.getElementById('saveFilter');
    
    saveFilterBtn.addEventListener('click', function() {
        const country = document.getElementById('country').value;
        const device = document.querySelector('input[name="device"]:checked').value;
        
        // Check if filter already exists
        const existingFilters = Array.from(activeFilters.querySelectorAll('.filter-tag'));
        const countryExists = existingFilters.some(tag => tag.dataset.value === country);
        const deviceExists = existingFilters.some(tag => tag.dataset.value === device);
        
        if (!countryExists) {
            const countryText = document.getElementById('country').options[document.getElementById('country').selectedIndex].text;
            const countryTag = document.createElement('span');
            countryTag.className = 'filter-tag';
            countryTag.dataset.value = country;
            countryTag.innerHTML = `${countryText} <i class="fas fa-times"></i>`;
            activeFilters.appendChild(countryTag);
            logToConsole(`Filtre ajouté: ${countryText}`);
        }
        
        if (!deviceExists) {
            const deviceTag = document.createElement('span');
            deviceTag.className = 'filter-tag';
            deviceTag.dataset.value = device;
            deviceTag.innerHTML = `${device.charAt(0).toUpperCase() + device.slice(1)} <i class="fas fa-times"></i>`;
            activeFilters.appendChild(deviceTag);
            logToConsole(`Filtre ajouté: ${device}`);
        }
    });
    
    // Compare button functionality
    const compareBtn = document.getElementById('compareBtn');
    const resultsSection = document.getElementById('resultsSection');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const resultsContent = document.getElementById('resultsContent');
    
    compareBtn.addEventListener('click', async function() {
        // Validate at least one keyword is entered
        const keyword1 = document.getElementById('keyword1').value.trim();
        
        if (!keyword1) {
            logToConsole('Veuillez entrer au moins un mot-clé', 'error');
            alert('Veuillez entrer au moins un mot-clé');
            return;
        }
        
        // Show results section and loading indicator
        resultsSection.style.display = 'block';
        loadingIndicator.style.display = 'flex';
        resultsContent.style.display = 'none';
        
        logToConsole('Début de la comparaison des SERPs...');
        
        // Collect form data
        const formData = new FormData();
        
        // Add keywords
        for (let i = 1; i <= 4; i++) {
            const keywordValue = document.getElementById(`keyword${i}`).value.trim();
            if (keywordValue) {
                formData.append(`keyword${i}`, keywordValue);
                logToConsole(`Mot-clé ${i}: ${keywordValue}`);
            }
        }
        
        // Add other form fields
        formData.append('country', document.getElementById('country').value);
        formData.append('location', document.getElementById('location').value);
        formData.append('search_engine', document.getElementById('search_engine').value);
        formData.append('num_results', document.getElementById('num_results').value);
        formData.append('language', document.getElementById('language').value);
        formData.append('device', document.querySelector('input[name="device"]:checked').value);
        
        try {
            logToConsole('Envoi de la requête au serveur...');
            
            const response = await fetch(window.getApiUrl('compare-serps'), {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            const data = await response.json();
            logToConsole('Réponse reçue du serveur');
            
            // Display results
            displayResults(data);
            
            // Hide loading indicator and show results
            loadingIndicator.style.display = 'none';
            resultsContent.style.display = 'block';
            
            logToConsole('Affichage des résultats terminé');
            
            // Scroll to results
            resultsSection.scrollIntoView({ behavior: 'smooth' });
            
        } catch (error) {
            logToConsole(`Erreur lors de la comparaison: ${error.message}`, 'error');
            alert(`Erreur lors de la comparaison: ${error.message}`);
            
            // Hide loading indicator
            loadingIndicator.style.display = 'none';
            resultsSection.style.display = 'none';
        }
    });
    
    // Function to display results
    function displayResults(data) {
        // Update detailed stats
        document.getElementById('exactMatchPercentage').textContent = `${data.analysis.exact_match.percentage}%`;
        document.getElementById('commonUrlsPercentage').textContent = `${data.analysis.common_urls.percentage}%`;
        document.getElementById('commonTitlesPercentage').textContent = `${data.analysis.common_titles.percentage}%`;
        document.getElementById('commonSnippetsPercentage').textContent = `${data.analysis.common_snippets.percentage}%`;
        
        // Update summary stats
        document.getElementById('similarityScore').textContent = `${Math.round(data.analysis.similarity_score * 100)}%`;
        document.getElementById('totalUrls').textContent = data.analysis.total_urls;
        
        // Update recommendation
        const recommendationBox = document.getElementById('recommendation');
        recommendationBox.textContent = data.analysis.recommendation;
        
        // Set recommendation color based on similarity score
        const similarityScore = data.analysis.similarity_score;
        if (similarityScore > 0.7) {
            recommendationBox.style.borderLeftColor = '#4caf50'; // Green for high similarity
        } else if (similarityScore > 0.4) {
            recommendationBox.style.borderLeftColor = '#ff9800'; // Orange for moderate similarity
        } else {
            recommendationBox.style.borderLeftColor = '#f44336'; // Red for low similarity
        }
        
        // Log detailed stats to console
        logToConsole(`Similarité exacte: ${data.analysis.exact_match.percentage}% (${data.analysis.exact_match.count} URLs)`);
        logToConsole(`URLs en commun: ${data.analysis.common_urls.percentage}% (${data.analysis.common_urls.count} URLs)`);
        logToConsole(`Titres en commun: ${data.analysis.common_titles.percentage}% (${data.analysis.common_titles.count} titres)`);
        logToConsole(`Snippets en commun: ${data.analysis.common_snippets.percentage}% (${data.analysis.common_snippets.count} snippets)`);
        logToConsole(`Score de similarité global: ${Math.round(data.analysis.similarity_score * 100)}%`);
        logToConsole(`URLs totales analysées: ${data.analysis.total_urls}`);
        
        // Display search intents
        const searchIntents = document.getElementById('searchIntents');
        searchIntents.innerHTML = '';
        
        // Process and display each search intent
        data.serp_results.forEach(serpResult => {
            const keyword = serpResult.keyword;
            const overallIntent = serpResult.overall_intent;
            const hasError = serpResult.error || (overallIntent && overallIntent.startsWith('Erreur'));
            
            // Create intent card
            const intentCard = document.createElement('div');
            intentCard.className = 'intent-card';
            
            if (hasError) {
                // Handle error case
                intentCard.classList.add('intent-error');
                intentCard.innerHTML = `
                    <div class="intent-keyword">${keyword}</div>
                    <div class="intent-type error">Erreur</div>
                    <div class="intent-explanation">${overallIntent}</div>
                    ${serpResult.error ? `<div class="intent-error-details">${serpResult.error}</div>` : ''}
                `;
                
                logToConsole(`Erreur pour "${keyword}": ${overallIntent}`, 'error');
            } else {
                // Parse intent type from the result (format expected: "Type d'intention - Explanation")
                let intentType = 'other';
                let intentExplanation = overallIntent;
                let intentTypeText = overallIntent;
                
                if (overallIntent && overallIntent.includes(' - ')) {
                    const parts = overallIntent.split(' - ');
                    const typeText = parts[0].toLowerCase();
                    intentTypeText = parts[0];
                    
                    if (typeText.includes('information')) {
                        intentType = 'informational';
                    } else if (typeText.includes('transaction')) {
                        intentType = 'transactional';
                    } else if (typeText.includes('navigation')) {
                        intentType = 'navigational';
                    } else if (typeText.includes('décision') || typeText.includes('decision')) {
                        intentType = 'decisionnelle';
                    }
                    
                    intentExplanation = parts.slice(1).join(' - ');
                }
                
                // Create intent card content
                intentCard.innerHTML = `
                    <div class="intent-keyword">${keyword}</div>
                    <div class="intent-type ${intentType}">${intentTypeText}</div>
                    <div class="intent-explanation">${intentExplanation}</div>
                `;
                
                logToConsole(`Intention de recherche globale pour "${keyword}": ${overallIntent}`);
            }
            
            searchIntents.appendChild(intentCard);
        });
        
        // Display SERP results
        const serpResultsGrid = document.getElementById('serpResultsGrid');
        serpResultsGrid.innerHTML = '';
        
        // Get all URLs that appear in multiple keywords
        const commonUrls = new Set();
        for (const [url, keywords] of Object.entries(getCommonUrls(data.serp_results))) {
            if (keywords.length > 1) {
                commonUrls.add(url);
            }
        }
        
        // Create a column for each keyword
        data.serp_results.forEach(serpResult => {
            const column = document.createElement('div');
            column.className = 'serp-column';
            column.innerHTML = `<h3>${serpResult.keyword}</h3>`;
            
            // Add each result
            serpResult.results.forEach((result, index) => {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'serp-result';
                
                // Add common indicator class if URL is common
                if (commonUrls.has(result.link)) {
                    resultDiv.classList.add('common-indicator');
                }
                
                // Get intent information if available
                const hasIntent = result.intent && result.intent !== 'Non analysé';
                let intentClass = 'other';
                
                if (hasIntent) {
                    const intentLower = result.intent.toLowerCase();
                    if (intentLower.includes('information')) {
                        intentClass = 'informationelle';
                    } else if (intentLower.includes('transaction')) {
                        intentClass = 'transactionnelle';
                    } else if (intentLower.includes('navigation')) {
                        intentClass = 'navigationnelle';
                    } else if (intentLower.includes('décision') || intentLower.includes('decision')) {
                        intentClass = 'decisionnelle';
                    }
                }
                
                // Create the result HTML
                let resultHTML = `
                    <div class="result-title">${result.title || 'Sans titre'}</div>
                    <div class="result-url">${result.link}</div>
                    <div class="result-snippet">${result.snippet || 'Pas de description'}</div>
                `;
                
                // Add intent information if available
                if (hasIntent) {
                    resultHTML += `
                        <div class="result-intent">
                            <span class="intent-badge ${intentClass}">${result.intent}</span>
                            <span class="intent-explanation-text">${result.intent_explanation || ''}</span>
                        </div>
                    `;
                }
                
                resultDiv.innerHTML = resultHTML;
                column.appendChild(resultDiv);
            });
            
            serpResultsGrid.appendChild(column);
        });
    }
    
    // Helper function to get common URLs
    function getCommonUrls(serpResults) {
        const urlMap = {};
        
        serpResults.forEach(serpResult => {
            const keyword = serpResult.keyword;
            
            serpResult.results.forEach(result => {
                const url = result.link;
                
                if (!urlMap[url]) {
                    urlMap[url] = [];
                }
                
                if (!urlMap[url].includes(keyword)) {
                    urlMap[url].push(keyword);
                }
            });
        });
        
        return urlMap;
    }
});
