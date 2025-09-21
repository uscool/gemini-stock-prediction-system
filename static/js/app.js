// Financial Analysis System Web Interface JavaScript

let availableAssets = {};
let currentAnalysis = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadAvailableAssets();
    checkSystemHealth();
    initializeRiskTolerance();
    loadSchedulerStatus();
    loadSchedules();
    checkUserAuthentication();
    
    // Show Analysis tab by default
    showAnalysisTab();
});

// Load available assets from API
async function loadAvailableAssets() {
    try {
        const response = await fetch('/api/assets');
        const data = await response.json();
        
        if (data.success) {
            availableAssets = data.data;
            updateAssetOptions();
            updateScheduleAssetOptions();
            console.log(`Loaded ${data.total_count} available assets`);
        } else {
            showError('Failed to load available assets');
        }
    } catch (error) {
        console.error('Error loading assets:', error);
        showError('Error connecting to analysis system');
    }
}

// Update asset selection dropdown based on type filter
function updateAssetOptions() {
    const assetType = document.getElementById('assetType').value;
    const assetSelect = document.getElementById('assetSelect');
    
    // Clear existing options
    assetSelect.innerHTML = '';
    
    let assetsToShow = [];
    
    switch(assetType) {
        case 'commodities':
            assetsToShow = availableAssets.commodities || [];
            break;
        case 'stocks':
            assetsToShow = availableAssets.stocks || [];
            break;
        default:
            assetsToShow = availableAssets.all || [];
    }
    
    // Add options
    assetsToShow.forEach(asset => {
        const option = document.createElement('option');
        option.value = asset;
        option.textContent = formatAssetName(asset);
        assetSelect.appendChild(option);
    });
}

// Format asset name for display
function formatAssetName(asset) {
    // Determine if it's a commodity or stock
    const isStock = availableAssets.stocks && availableAssets.stocks.includes(asset);
    const isCommodity = availableAssets.commodities && availableAssets.commodities.includes(asset);
    
    let formatted = asset.replace(/_/g, ' ').toUpperCase();
    
    if (isStock) {
        formatted = `📈 ${formatted}`;
    } else if (isCommodity) {
        formatted = `📊 ${formatted}`;
    }
    
    return formatted;
}

// Get the proper symbol for an asset
function getAssetSymbol(assetName, assetType) {
    const symbolMap = {
        // Commodities
        'gold': 'GC=F',
        'silver': 'SI=F',
        'crude_oil': 'CL=F',
        'natural_gas': 'NG=F',
        'copper': 'HG=F',
        'wheat': 'ZW=F',
        'corn': 'ZC=F',
        'soybeans': 'ZS=F',
        'coffee': 'KC=F',
        'sugar': 'SB=F',
        'cotton': 'CT=F',
        'platinum': 'PL=F',
        'palladium': 'PA=F',
        'aluminum': 'ALI=F',
        'zinc': 'ZNC=F',
        
        // Stocks
        'apple': 'AAPL',
        'microsoft': 'MSFT',
        'google': 'GOOGL',
        'amazon': 'AMZN',
        'tesla': 'TSLA',
        'nvidia': 'NVDA',
        'meta': 'META',
        'netflix': 'NFLX',
        'adobe': 'ADBE',
        'salesforce': 'CRM',
        'oracle': 'ORCL',
        'intel': 'INTC',
        'amd': 'AMD',
        'cisco': 'CSCO',
        'ibm': 'IBM',
        'berkshire_hathaway': 'BRK-B',
        'jpmorgan': 'JPM',
        'bank_of_america': 'BAC',
        'wells_fargo': 'WFC',
        'goldman_sachs': 'GS',
        'morgan_stanley': 'MS',
        'american_express': 'AXP',
        'visa': 'V',
        'mastercard': 'MA',
        'paypal': 'PYPL',
        'johnson_johnson': 'JNJ',
        'pfizer': 'PFE',
        'moderna': 'MRNA',
        'abbvie': 'ABBV',
        'merck': 'MRK',
        'bristol_myers': 'BMY',
        'eli_lilly': 'LLY',
        'unitedhealth': 'UNH',
        'walmart': 'WMT',
        'coca_cola': 'KO',
        'pepsi': 'PEP',
        'procter_gamble': 'PG',
        'nike': 'NKE',
        'mcdonalds': 'MCD',
        'starbucks': 'SBUX',
        'home_depot': 'HD',
        'target': 'TGT',
        'exxon_mobil': 'XOM',
        'chevron': 'CVX',
        'conocophillips': 'COP',
        'marathon_petroleum': 'MPC',
        'boeing': 'BA'
    };
    
    return symbolMap[assetName] || null;
}

// Get asset name from symbol
function getAssetNameFromSymbol(symbol) {
    const reverseMap = {
        // Commodities
        'GC=F': 'gold',
        'SI=F': 'silver',
        'CL=F': 'crude_oil',
        'NG=F': 'natural_gas',
        'HG=F': 'copper',
        'ZW=F': 'wheat',
        'ZC=F': 'corn',
        'ZS=F': 'soybeans',
        'KC=F': 'coffee',
        'SB=F': 'sugar',
        'CT=F': 'cotton',
        'PL=F': 'platinum',
        'PA=F': 'palladium',
        'ALI=F': 'aluminum',
        'ZNC=F': 'zinc',
        
        // Stocks
        'AAPL': 'apple',
        'MSFT': 'microsoft',
        'GOOGL': 'google',
        'AMZN': 'amazon',
        'TSLA': 'tesla',
        'NVDA': 'nvidia',
        'META': 'meta',
        'NFLX': 'netflix',
        'ADBE': 'adobe',
        'CRM': 'salesforce',
        'ORCL': 'oracle',
        'INTC': 'intel',
        'AMD': 'amd',
        'CSCO': 'cisco',
        'IBM': 'ibm',
        'BRK-B': 'berkshire_hathaway',
        'JPM': 'jpmorgan',
        'BAC': 'bank_of_america',
        'WFC': 'wells_fargo',
        'GS': 'goldman_sachs',
        'MS': 'morgan_stanley',
        'AXP': 'american_express',
        'V': 'visa',
        'MA': 'mastercard',
        'PYPL': 'paypal',
        'JNJ': 'johnson_johnson',
        'PFE': 'pfizer',
        'MRNA': 'moderna',
        'ABBV': 'abbvie',
        'MRK': 'merck',
        'BMY': 'bristol_myers',
        'LLY': 'eli_lilly',
        'UNH': 'unitedhealth',
        'WMT': 'walmart',
        'KO': 'coca_cola',
        'PEP': 'pepsi',
        'PG': 'procter_gamble',
        'NKE': 'nike',
        'MCD': 'mcdonalds',
        'SBUX': 'starbucks',
        'HD': 'home_depot',
        'TGT': 'target',
        'XOM': 'exxon_mobil',
        'CVX': 'chevron',
        'COP': 'conocophillips',
        'MPC': 'marathon_petroleum',
        'BA': 'boeing'
    };
    
    return reverseMap[symbol] || symbol;
}

// Get asset type from symbol
function getAssetTypeFromSymbol(symbol) {
    const commoditySymbols = ['GC=F', 'SI=F', 'CL=F', 'NG=F', 'HG=F', 'ZW=F', 'ZC=F', 'ZS=F', 'KC=F', 'SB=F', 'CT=F', 'PL=F', 'PA=F', 'ALI=F', 'ZNC=F'];
    return commoditySymbols.includes(symbol) ? 'commodity' : 'stock';
}

// Update schedule asset selection dropdown
function updateScheduleAssetOptions() {
    const scheduleAssetSelect = document.getElementById('scheduleAssets');
    if (!scheduleAssetSelect) return;
    
    // Clear existing options
    scheduleAssetSelect.innerHTML = '';
    
    // Add all assets
    const allAssets = availableAssets.all || [];
    
    allAssets.forEach(asset => {
        const option = document.createElement('option');
        option.value = asset;
        option.textContent = formatAssetName(asset);
        scheduleAssetSelect.appendChild(option);
    });
}

// Quick select asset
function selectAsset(asset) {
    const assetSelect = document.getElementById('assetSelect');
    
    // Clear previous selections
    for (let option of assetSelect.options) {
        option.selected = false;
    }
    
    // Select the target asset
    for (let option of assetSelect.options) {
        if (option.value === asset) {
            option.selected = true;
            break;
        }
    }
}

// Run analysis
async function runAnalysis() {
    const assetSelect = document.getElementById('assetSelect');
    const selectedAssets = Array.from(assetSelect.selectedOptions).map(option => option.value);
    
    if (selectedAssets.length === 0) {
        showError('Please select at least one asset to analyze');
        return;
    }
    
    const timeframe = parseInt(document.getElementById('timeframe').value);
    const sendEmail = document.getElementById('sendEmail').checked;
    const riskTolerance = document.getElementById('riskTolerance').value;
    
    // Show loading
    showLoading();
    
    try {
        const token = await getCSRFToken();
        let response;
        
        if (selectedAssets.length === 1) {
            // Single asset analysis
            response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': token
                },
                body: JSON.stringify({
                    asset: selectedAssets[0],
                    timeframe: timeframe,
                    send_email: sendEmail,
                    risk_tolerance: riskTolerance
                })
            });
        } else {
            // Multiple asset analysis
            response = await fetch('/api/analyze-multiple', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': token
                },
                body: JSON.stringify({
                    assets: selectedAssets,
                    timeframe: timeframe,
                    send_individual_emails: false,
                    send_summary_email: sendEmail,
                    risk_tolerance: riskTolerance
                })
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentAnalysis = result.data;
            displayResults(result.data);
            updateWebsiteLog(result.data.websites_accessed || []);
        } else {
            showError(result.error || 'Analysis failed');
        }
        
    } catch (error) {
        console.error('Analysis error:', error);
        showError('Error running analysis: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Get AI-generated search terms preview
async function getSearchTerms() {
    const assetSelect = document.getElementById('assetSelect');
    const selectedAssets = Array.from(assetSelect.selectedOptions).map(option => option.value);
    
    if (selectedAssets.length === 0) {
        showError('Please select an asset to preview search terms');
        return;
    }
    
    if (selectedAssets.length > 1) {
        showError('Please select only one asset for search terms preview');
        return;
    }
    
    const asset = selectedAssets[0];
    const timeframe = parseInt(document.getElementById('timeframe').value);
    
    showLoading();
    
    try {
        const response = await fetch(`/api/search-terms/${asset}?timeframe=${timeframe}`);
        const result = await response.json();
        
        if (result.success) {
            displaySearchTerms(result.data);
        } else {
            showError(result.error || 'Failed to generate search terms');
        }
        
    } catch (error) {
        console.error('Search terms error:', error);
        showError('Error generating search terms: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Display analysis results
function displayResults(data) {
    hideWelcome();
    hideSearchTerms();
    
    if (data.analysis_type === 'multi_commodity' || data.successful_analyses) {
        // Multiple asset analysis
        displayMultipleAssetResults(data);
    } else {
        // Single asset analysis
        displaySingleAssetResults(data);
    }
    
    showResults();
}

// Display single asset results
function displaySingleAssetResults(data) {
    const asset = data.asset || 'Unknown';
    const assetType = data.asset_type || 'unknown';
    const tradingDecision = data.trading_decision || {};
    const sentimentAnalysis = data.sentiment_analysis || {};
    const dataAnalysis = data.data_analysis || {};
    
    // Analysis Results Summary
    const analysisResults = document.getElementById('analysisResults');
    analysisResults.innerHTML = `
        <div class="row">
            <div class="col-md-6 col-lg-4">
                <div class="metric-card">
                    <div class="metric-label">Asset</div>
                    <div class="metric-value">${formatAssetName(asset)} (${assetType})</div>
                </div>
            </div>
            <div class="col-md-6 col-lg-4">
                <div class="metric-card">
                    <div class="metric-label">Current Price</div>
                    <div class="metric-value">$${(dataAnalysis.current_price || 0).toFixed(4)}</div>
                </div>
            </div>
            <div class="col-md-6 col-lg-4">
                <div class="metric-card">
                    <div class="metric-label">Risk Tolerance</div>
                    <div class="metric-value">${getRiskToleranceDisplay(data.risk_tolerance || 'moderate')}</div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="metric-card">
                    <div class="metric-label">Sentiment Score</div>
                    <div class="metric-value">${(sentimentAnalysis.normalized_score || 50).toFixed(1)}/100</div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="metric-card">
                    <div class="metric-label">Trend Score</div>
                    <div class="metric-value">${(dataAnalysis.trend_score || 50).toFixed(1)}/100</div>
                </div>
            </div>
        </div>
    `;
    
    // Trading Decision
    const decision = tradingDecision.decision || 'UNKNOWN';
    const confidence = tradingDecision.confidence || 0;
    const reasoning = tradingDecision.reasoning || 'No reasoning available';
    
    const decisionClass = decision === 'BUY' ? 'decision-buy' : 
                         decision === 'SELL' ? 'decision-sell' : 'decision-hold';
    
    const tradingDecisionEl = document.getElementById('tradingDecision');
    tradingDecisionEl.innerHTML = `
        <div class="${decisionClass}">
            <h3><i class="fas fa-${decision === 'BUY' ? 'arrow-up' : decision === 'SELL' ? 'arrow-down' : 'minus'}"></i> ${decision}</h3>
            <div class="confidence-bar mt-2">
                <div class="confidence-fill confidence-${confidence > 0.7 ? 'high' : confidence > 0.4 ? 'medium' : 'low'}" 
                     style="width: ${confidence * 100}%"></div>
            </div>
            <p class="mt-2 mb-1"><strong>Confidence:</strong> ${(confidence * 100).toFixed(0)}%</p>
            <p class="small mb-0">${reasoning}</p>
        </div>
        
        ${tradingDecision.target_price ? `<p><strong>Target Price:</strong> $${tradingDecision.target_price}</p>` : ''}
        ${tradingDecision.stop_loss ? `<p><strong>Stop Loss:</strong> $${tradingDecision.stop_loss}</p>` : ''}
        <p><strong>Position Size:</strong> ${tradingDecision.position_size || 'MEDIUM'}</p>
        <p><strong>Risk Level:</strong> ${tradingDecision.risk_level || 'MEDIUM'}</p>
    `;
    
    // Technical Analysis
    const technical = dataAnalysis.technical_indicators || {};
    const priceAnalysis = dataAnalysis.price_analysis || {};
    const volatility = dataAnalysis.volatility_analysis || {};
    
    const technicalAnalysisEl = document.getElementById('technicalAnalysis');
    technicalAnalysisEl.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>Price Analysis</h6>
                <ul class="list-unstyled">
                    <li><strong>Decision Period Change:</strong> ${(priceAnalysis.decision_period_change || 0).toFixed(2)}%</li>
                    <li><strong>Performance Percentile:</strong> ${(priceAnalysis.performance_percentile || 50).toFixed(1)}%</li>
                    <li><strong>Recent Trend:</strong> ${priceAnalysis.recent_trend || 'neutral'}</li>
                    <li><strong>Data Points:</strong> ${dataAnalysis.data_points || 0}</li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6>Technical Indicators</h6>
                <ul class="list-unstyled">
                    <li><strong>RSI:</strong> ${technical.rsi ? technical.rsi.toFixed(1) : 'N/A'} ${technical.rsi_signal ? `(${technical.rsi_signal})` : ''}</li>
                    <li><strong>MACD Trend:</strong> ${technical.macd_trend || 'neutral'}</li>
                    <li><strong>Volatility:</strong> ${volatility.annualized_volatility ? volatility.annualized_volatility.toFixed(2) + '%' : 'N/A'}</li>
                    <li><strong>Volume Trend:</strong> ${dataAnalysis.volume_analysis?.volume_trend || 'neutral'}</li>
                </ul>
            </div>
        </div>
        
        <div class="analysis-timestamp">
            Analysis completed: ${new Date(data.analysis_timestamp).toLocaleString()}
        </div>
    `;
    
    // Display news articles
    displayNewsArticles(sentimentAnalysis);
}

// Display multiple asset results
function displayMultipleAssetResults(data) {
    const successfulAnalyses = data.successful_analyses || [];
    const failedAnalyses = data.failed_analyses || [];
    
    // Analysis Results Summary
    const analysisResults = document.getElementById('analysisResults');
    analysisResults.innerHTML = `
        <div class="row mb-3">
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-label">Total Assets</div>
                    <div class="metric-value">${successfulAnalyses.length + failedAnalyses.length}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-label">Successful</div>
                    <div class="metric-value text-success">${successfulAnalyses.length}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-label">Failed</div>
                    <div class="metric-value text-danger">${failedAnalyses.length}</div>
                </div>
            </div>
        </div>
        
        <h6>Individual Recommendations:</h6>
        <div class="row">
            ${successfulAnalyses.map(analysis => {
                const asset = analysis.asset || 'Unknown';
                const assetType = analysis.asset_type || 'unknown';
                const decision = analysis.trading_decision?.decision || 'UNKNOWN';
                const confidence = analysis.trading_decision?.confidence || 0;
                const price = analysis.data_analysis?.current_price || 0;
                const trendScore = analysis.data_analysis?.trend_score || 50;
                
                const decisionColor = decision === 'BUY' ? 'success' : 
                                    decision === 'SELL' ? 'danger' : 'warning';
                const typeIcon = assetType === 'stock' ? '📈' : '📊';
                
                return `
                    <div class="col-md-6 mb-2">
                        <div class="card">
                            <div class="card-body">
                                <h6>${typeIcon} ${asset.toUpperCase()}</h6>
                                <p class="mb-1"><strong>Price:</strong> $${price.toFixed(4)}</p>
                                <p class="mb-1"><strong>Trend:</strong> ${trendScore.toFixed(1)}/100</p>
                                <span class="badge bg-${decisionColor}">${decision} (${(confidence * 100).toFixed(0)}%)</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
    
    // Market Summary (if available)
    const marketSummary = data.market_summary;
    if (marketSummary && !marketSummary.error) {
        const tradingDecisionEl = document.getElementById('tradingDecision');
        tradingDecisionEl.innerHTML = `
            <h5>Market Summary</h5>
            <div class="alert alert-info">
                <p><strong>Overall Sentiment:</strong> ${marketSummary.overall_market_sentiment || 'NEUTRAL'}</p>
                <p><strong>Market Confidence:</strong> ${((marketSummary.market_confidence || 0.5) * 100).toFixed(0)}%</p>
                <p><strong>Summary:</strong> ${marketSummary.market_summary || 'Analysis completed'}</p>
            </div>
            
            ${marketSummary.top_opportunities && marketSummary.top_opportunities.length > 0 ? `
                <h6>Top Opportunities:</h6>
                <ul>
                    ${marketSummary.top_opportunities.map(opp => `<li>${opp}</li>`).join('')}
                </ul>
            ` : ''}
            
            ${marketSummary.top_risks && marketSummary.top_risks.length > 0 ? `
                <h6>Key Risks:</h6>
                <ul>
                    ${marketSummary.top_risks.map(risk => `<li>${risk}</li>`).join('')}
                </ul>
            ` : ''}
        `;
    } else {
        document.getElementById('tradingDecision').innerHTML = '<p class="text-muted">Market summary not available</p>';
    }
    
    // Technical Analysis Summary
    document.getElementById('technicalAnalysis').innerHTML = `
        <p>Detailed technical analysis available for each individual asset in the results above.</p>
        <div class="analysis-timestamp">
            Analysis completed: ${new Date(data.analysis_timestamp).toLocaleString()}
        </div>
    `;
}

// Display search terms
function displaySearchTerms(data) {
    hideWelcome();
    hideResults();
    
    const searchTermsResults = document.getElementById('searchTermsResults');
    searchTermsResults.innerHTML = `
        <h6>Search Terms for ${formatAssetName(data.asset)} (${data.timeframe} days)</h6>
        <p class="text-muted">These AI-generated search terms will be used to find relevant news articles:</p>
        
        <div class="mb-3">
            ${data.search_terms.map(term => `<span class="search-term-badge">${term}</span>`).join('')}
        </div>
        
        <div class="alert alert-info">
            <i class="fas fa-lightbulb me-2"></i>
            <strong>Total Terms:</strong> ${data.count} | 
            <strong>Generated by:</strong> Google Gemini AI
        </div>
    `;
    
    showSearchTerms();
}

// Update website access log
function updateWebsiteLog(websites) {
    const websiteLog = document.getElementById('websiteLog');
    
    if (!websites || websites.length === 0) {
        websiteLog.innerHTML = '<p class="text-muted">No websites accessed yet</p>';
        return;
    }
    
    const uniqueWebsites = {};
    websites.forEach(site => {
        const key = `${site.source}_${site.url}`;
        if (!uniqueWebsites[key]) {
            uniqueWebsites[key] = site;
        }
    });
    
    const uniqueList = Object.values(uniqueWebsites);
    
    const successfulSites = uniqueList.filter(site => site.status === 'loaded' || site.status === 'accessed');
    const failedSites = uniqueList.filter(site => site.status && site.status.includes('failed'));
    
    websiteLog.innerHTML = `
        <div class="mb-2">
            <small class="text-success">✅ ${successfulSites.length} successful</small> | 
            <small class="text-danger">❌ ${failedSites.length} failed</small> | 
            <small class="text-muted">Total: ${uniqueList.length} sites</small>
        </div>
        ${uniqueList.map(site => {
            const isSuccess = site.status === 'loaded' || site.status === 'accessed';
            const statusIcon = isSuccess ? '✅' : '❌';
            const statusClass = isSuccess ? 'border-success' : 'border-danger';
            
            return `
                <div class="website-log-item ${statusClass}" style="border-left-width: 3px;">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="source">${statusIcon} ${site.source}</div>
                            <div class="url">${truncateUrl(site.url, 40)}</div>
                            ${site.search_term ? `<div class="small text-muted">🔍 "${site.search_term}"</div>` : ''}
                        </div>
                        <small class="text-muted">${new Date(site.timestamp).toLocaleTimeString()}</small>
                    </div>
                </div>
            `;
        }).join('')}
    `;
}

// Utility functions
function truncateUrl(url, maxLength = 50) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

function showLoading() {
    document.getElementById('loadingSpinner').classList.remove('d-none');
}

function hideLoading() {
    document.getElementById('loadingSpinner').classList.add('d-none');
}

function showResults() {
    document.getElementById('resultsSection').classList.remove('d-none');
}

function hideResults() {
    document.getElementById('resultsSection').classList.add('d-none');
}

function showSearchTerms() {
    document.getElementById('searchTermsSection').classList.remove('d-none');
}

function hideSearchTerms() {
    document.getElementById('searchTermsSection').classList.add('d-none');
}

function hideWelcome() {
    document.getElementById('welcomeSection').classList.add('d-none');
}

function showWelcome() {
    document.getElementById('welcomeSection').classList.remove('d-none');
}

function clearResults() {
    hideResults();
    hideSearchTerms();
    showWelcome();
    
    // Clear website log
    document.getElementById('websiteLog').innerHTML = '<p class="text-muted">No analysis run yet</p>';
    
    currentAnalysis = null;
}

function showError(message) {
    const alertHtml = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at top of container
    const container = document.querySelector('.container');
    const firstChild = container.firstElementChild;
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHtml;
    container.insertBefore(alertDiv, firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        const alert = alertDiv.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

function showSuccess(message) {
    const alertHtml = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="fas fa-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at top of container
    const container = document.querySelector('.container');
    const firstChild = container.firstElementChild;
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHtml;
    container.insertBefore(alertDiv, firstChild);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        const alert = alertDiv.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 3000);
}

// Check system health
async function checkSystemHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        if (data.success && data.analyzer_initialized) {
            console.log('✅ System health check passed');
        } else {
            showError('System not fully initialized - some features may not work');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        showError('Unable to connect to analysis system');
    }
}

// Export current analysis results
function exportResults() {
    if (!currentAnalysis) {
        showError('No analysis results to export');
        return;
    }
    
    const dataStr = JSON.stringify(currentAnalysis, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `analysis_${currentAnalysis.asset || 'multi'}_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    
    showSuccess('Analysis results exported successfully');
}

// Add export button to results (called after displaying results)
function addExportButton() {
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection && !document.getElementById('exportButton')) {
        const exportButton = document.createElement('button');
        exportButton.id = 'exportButton';
        exportButton.className = 'btn btn-outline-secondary mt-3';
        exportButton.innerHTML = '<i class="fas fa-download me-2"></i>Export Results';
        exportButton.onclick = exportResults;
        resultsSection.appendChild(exportButton);
    }
}

// Display news articles that were analyzed
function displayNewsArticles(sentimentAnalysis) {
    const newsArticlesEl = document.getElementById('newsArticles');
    
    if (!sentimentAnalysis || !sentimentAnalysis.individual_results) {
        newsArticlesEl.innerHTML = '<p class="text-muted">No news articles were collected for this analysis.</p>';
        return;
    }
    
    const articles = sentimentAnalysis.individual_results;
    const totalArticles = sentimentAnalysis.total_articles || articles.length;
    const sentimentBreakdown = sentimentAnalysis.sentiment_breakdown || {};
    
    if (articles.length === 0) {
        newsArticlesEl.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>No articles found</strong><br>
                No relevant news articles were found for this analysis. This may be due to:
                <ul class="mb-0 mt-2">
                    <li>Network connectivity issues</li>
                    <li>Limited recent news coverage</li>
                    <li>RSS feed availability</li>
                </ul>
            </div>
        `;
        return;
    }
    
    // Calculate actual counts from articles instead of using percentages
    const positiveCount = articles.filter(article => article.sentiment === 'positive').length;
    const negativeCount = articles.filter(article => article.sentiment === 'negative').length;
    const neutralCount = articles.filter(article => article.sentiment === 'neutral').length;
    
    // Group articles by source
    const articlesBySource = {};
    articles.forEach(article => {
        const source = article.source || 'Unknown';
        if (!articlesBySource[source]) {
            articlesBySource[source] = [];
        }
        articlesBySource[source].push(article);
    });
    
    newsArticlesEl.innerHTML = `
        <div class="row mb-3">
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Total Articles</div>
                    <div class="metric-value">${totalArticles}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Positive</div>
                    <div class="metric-value text-success">${positiveCount}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Negative</div>
                    <div class="metric-value text-danger">${negativeCount}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Neutral</div>
                    <div class="metric-value text-secondary">${neutralCount}</div>
                </div>
            </div>
        </div>
        
        <div class="accordion" id="articlesAccordion">
            ${Object.entries(articlesBySource).map(([source, sourceArticles], sourceIndex) => `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading${sourceIndex}">
                        <button class="accordion-button ${sourceIndex === 0 ? '' : 'collapsed'}" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#collapse${sourceIndex}" 
                                aria-expanded="${sourceIndex === 0 ? 'true' : 'false'}" aria-controls="collapse${sourceIndex}">
                            <strong>${source}</strong> <span class="badge bg-secondary ms-2">${sourceArticles.length}</span>
                        </button>
                    </h2>
                    <div id="collapse${sourceIndex}" class="accordion-collapse collapse ${sourceIndex === 0 ? 'show' : ''}" 
                         aria-labelledby="heading${sourceIndex}" data-bs-parent="#articlesAccordion">
                        <div class="accordion-body">
                            ${sourceArticles.map((article, articleIndex) => {
                                const sentimentClass = article.sentiment === 'positive' ? 'success' : 
                                                     article.sentiment === 'negative' ? 'danger' : 'secondary';
                                const sentimentIcon = article.sentiment === 'positive' ? 'fa-thumbs-up' : 
                                                    article.sentiment === 'negative' ? 'fa-thumbs-down' : 'fa-minus';
                                
                                return `
                                    <div class="article-item mb-3 p-3 border rounded">
                                        <div class="d-flex justify-content-between align-items-start mb-2">
                                            <h6 class="mb-1">
                                                <a href="${article.url || '#'}" target="_blank" class="text-decoration-none">
                                                    ${article.title || 'Untitled Article'}
                                                    <i class="fas fa-external-link-alt fa-sm ms-1"></i>
                                                </a>
                                            </h6>
                                            <div class="d-flex align-items-center">
                                                <span class="badge bg-${sentimentClass}">
                                                    <i class="fas ${sentimentIcon} me-1"></i>
                                                    ${article.sentiment || 'neutral'}
                                                </span>
                                                <small class="text-muted ms-2">${(article.confidence * 100 || 0).toFixed(0)}%</small>
                                            </div>
                                        </div>
                                        
                                        <p class="small text-muted mb-2">
                                            <i class="fas fa-calendar me-1"></i>
                                            ${new Date(article.date).toLocaleDateString()} | 
                                            <i class="fas fa-chart-bar me-1"></i>
                                            Score: ${(article.score || 0).toFixed(2)}
                                        </p>
                                        
                                        <p class="mb-0 small">${truncateText(article.content || 'No content available', 200)}</p>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="mt-3">
            <small class="text-muted">
                <i class="fas fa-info-circle me-1"></i>
                Articles are analyzed using FinBERT for financial sentiment classification.
                Click article titles to read the full content on the original website.
            </small>
        </div>
    `;
}

// Truncate text to specified length
function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Initialize risk tolerance functionality
function initializeRiskTolerance() {
    const riskToleranceSelect = document.getElementById('riskTolerance');
    const riskDescriptionEl = document.getElementById('riskDescription');
    
    const riskDescriptions = {
        'conservative': 'Focus on capital preservation with minimal risk. Prefers stable, dividend-paying assets.',
        'moderate': 'Balanced approach with moderate risk for steady returns. Good mix of growth and safety.',
        'aggressive': 'Higher risk tolerance for potentially higher returns. Growth-focused investments.',
        'very_aggressive': 'Maximum risk tolerance for maximum potential returns. Speculative investments welcome.'
    };
    
    // Update description when selection changes
    riskToleranceSelect.addEventListener('change', function() {
        const selectedRisk = this.value;
        riskDescriptionEl.textContent = riskDescriptions[selectedRisk];
        
        // Update form styling based on risk level
        const formGroup = this.closest('.mb-3');
        formGroup.className = formGroup.className.replace(/risk-\w+/g, '');
        formGroup.classList.add(`risk-${selectedRisk.replace('_', '-')}`);
    });
    
    // Set initial description
    riskDescriptionEl.textContent = riskDescriptions[riskToleranceSelect.value];
}

// Get risk tolerance display with icon
function getRiskToleranceDisplay(riskTolerance) {
    const displays = {
        'conservative': '🛡️ Conservative',
        'moderate': '⚖️ Moderate', 
        'aggressive': '🚀 Aggressive',
        'very_aggressive': '⚡ Very Aggressive'
    };
    return displays[riskTolerance] || '⚖️ Moderate';
}

// Tab switching functions
function showAnalysisTab() {
    // Hide all tabs
    document.getElementById('analysisTab').classList.remove('d-none');
    document.getElementById('schedulerTab').classList.add('d-none');
    document.getElementById('portfolioTab').classList.add('d-none');
}

function showSchedulerTab() {
    // Hide all tabs
    document.getElementById('analysisTab').classList.add('d-none');
    document.getElementById('schedulerTab').classList.remove('d-none');
    document.getElementById('portfolioTab').classList.add('d-none');
    loadSchedulerStatus();
    loadSchedules();
}

// Scheduler functions
async function loadSchedulerStatus() {
    try {
        const response = await fetch('/api/scheduler/status');
        const data = await response.json();
        
        if (data.success) {
            const status = data.data;
            const statusEl = document.getElementById('schedulerStatus');
            
            const statusClass = status.running ? 'success' : 'danger';
            const statusIcon = status.running ? 'fa-play-circle' : 'fa-pause-circle';
            
            statusEl.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span><i class="fas ${statusIcon} text-${statusClass} me-2"></i>Status:</span>
                    <span class="badge bg-${statusClass}">${status.running ? 'Running' : 'Stopped'}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>Total Schedules:</span>
                    <span class="badge bg-secondary">${status.total_schedules}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>Enabled Schedules:</span>
                    <span class="badge bg-primary">${status.enabled_schedules}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>Analyzer:</span>
                    <span class="badge bg-${status.analyzer_initialized ? 'success' : 'danger'}">
                        ${status.analyzer_initialized ? 'Ready' : 'Not Ready'}
                    </span>
                </div>
                ${status.next_scheduled_run ? `
                    <div class="mt-2">
                        <small class="text-muted">
                            <i class="fas fa-clock me-1"></i>
                            Next run: ${new Date(status.next_scheduled_run).toLocaleString()}
                        </small>
                    </div>
                ` : ''}
            `;
        }
    } catch (error) {
        console.error('Error loading scheduler status:', error);
        document.getElementById('schedulerStatus').innerHTML = '<p class="text-danger">Error loading status</p>';
    }
}

async function loadSchedules() {
    try {
        const response = await fetch('/api/schedules');
        const data = await response.json();
        
        if (data.success) {
            const schedules = data.data;
            const schedulesListEl = document.getElementById('schedulesList');
            
            if (Object.keys(schedules).length === 0) {
                schedulesListEl.innerHTML = `
                    <div class="text-center text-muted">
                        <i class="fas fa-clock fa-3x mb-3"></i>
                        <p>No schedules created yet.</p>
                        <p>Create your first schedule using the form on the left.</p>
                    </div>
                `;
                return;
            }
            
            schedulesListEl.innerHTML = Object.values(schedules).map(schedule => {
                const isEnabled = schedule.enabled;
                const statusClass = isEnabled ? 'success' : 'secondary';
                const statusIcon = isEnabled ? 'fa-play' : 'fa-pause';
                
                const nextRun = schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'Not scheduled';
                const lastRun = schedule.last_run ? new Date(schedule.last_run).toLocaleString() : 'Never';
                
                return `
                    <div class="card mb-3">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="mb-0">${schedule.name}</h6>
                                <div class="d-flex gap-1">
                                    <span class="badge bg-${statusClass}">
                                        <i class="fas ${statusIcon} me-1"></i>
                                        ${isEnabled ? 'Enabled' : 'Disabled'}
                                    </span>
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteSchedule('${schedule.id}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                            
                            <div class="row mb-2">
                                <div class="col-md-6">
                                    <small class="text-muted">
                                        <i class="fas fa-chart-line me-1"></i>
                                        Assets: ${schedule.assets.join(', ')}
                                    </small>
                                </div>
                                <div class="col-md-6">
                                    <small class="text-muted">
                                        <i class="fas fa-calendar me-1"></i>
                                        ${schedule.frequency} at ${schedule.time_of_day}
                                    </small>
                                </div>
                            </div>
                            
                            <div class="row mb-2">
                                <div class="col-md-4">
                                    <small class="text-muted">
                                        <i class="fas fa-clock me-1"></i>
                                        Next: ${nextRun}
                                    </small>
                                </div>
                                <div class="col-md-4">
                                    <small class="text-muted">
                                        <i class="fas fa-history me-1"></i>
                                        Last: ${lastRun}
                                    </small>
                                </div>
                                <div class="col-md-4">
                                    <small class="text-muted">
                                        <i class="fas fa-chart-bar me-1"></i>
                                        Runs: ${schedule.run_count || 0} (${schedule.success_count || 0} success)
                                    </small>
                                </div>
                            </div>
                            
                            <div class="d-flex gap-2">
                                <button class="btn btn-outline-primary btn-sm" onclick="runScheduleNow('${schedule.id}')">
                                    <i class="fas fa-play me-1"></i>Run Now
                                </button>
                                <button class="btn btn-outline-secondary btn-sm" onclick="toggleSchedule('${schedule.id}', ${!isEnabled})">
                                    <i class="fas fa-${isEnabled ? 'pause' : 'play'} me-1"></i>
                                    ${isEnabled ? 'Disable' : 'Enable'}
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading schedules:', error);
        document.getElementById('schedulesList').innerHTML = '<p class="text-danger">Error loading schedules</p>';
    }
}

async function createSchedule() {
    const name = document.getElementById('scheduleName').value.trim();
    const assets = Array.from(document.getElementById('scheduleAssets').selectedOptions).map(option => option.value);
    const timeframe = parseInt(document.getElementById('scheduleTimeframe').value);
    const frequency = document.getElementById('scheduleFrequency').value;
    const timeOfDay = document.getElementById('scheduleTime').value;
    const riskTolerance = document.getElementById('scheduleRiskTolerance').value;
    const sendEmail = document.getElementById('scheduleSendEmail').checked;
    const enabled = document.getElementById('scheduleEnabled').checked;
    
    if (!name) {
        showError('Please enter a schedule name');
        return;
    }
    
    if (assets.length === 0) {
        showError('Please select at least one asset');
        return;
    }
    
    try {
        const token = await getCSRFToken();
        const response = await fetch('/api/schedules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                name: name,
                assets: assets,
                timeframe: timeframe,
                frequency: frequency,
                time_of_day: timeOfDay,
                risk_tolerance: riskTolerance,
                send_email: sendEmail,
                enabled: enabled
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Schedule created successfully!');
            document.getElementById('scheduleForm').reset();
            document.getElementById('scheduleTime').value = '09:00';
            document.getElementById('scheduleSendEmail').checked = true;
            document.getElementById('scheduleEnabled').checked = true;
            loadSchedules();
            loadSchedulerStatus();
        } else {
            showError(result.error || 'Failed to create schedule');
        }
        
    } catch (error) {
        console.error('Error creating schedule:', error);
        showError('Error creating schedule: ' + error.message);
    }
}

async function deleteSchedule(scheduleId) {
    if (!confirm('Are you sure you want to delete this schedule?')) {
        return;
    }
    
    try {
        const token = await getCSRFToken();
        const response = await fetch(`/api/schedules/${scheduleId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': token
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Schedule deleted successfully!');
            loadSchedules();
            loadSchedulerStatus();
        } else {
            showError(result.error || 'Failed to delete schedule');
        }
        
    } catch (error) {
        console.error('Error deleting schedule:', error);
        showError('Error deleting schedule: ' + error.message);
    }
}

async function runScheduleNow(scheduleId) {
    try {
        console.log('Running schedule:', scheduleId);
        const token = await getCSRFToken();
        console.log('CSRF token retrieved:', token ? 'Yes' : 'No');
        
        const response = await fetch(`/api/schedules/${scheduleId}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            }
        });
        
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Response result:', result);
        
        if (result.success) {
            showSuccess('Schedule triggered successfully!');
            loadSchedules();
        } else {
            showError(result.error || 'Failed to run schedule');
        }
        
    } catch (error) {
        console.error('Error running schedule:', error);
        showError('Error running schedule: ' + error.message);
    }
}

async function toggleSchedule(scheduleId, enabled) {
    try {
        const token = await getCSRFToken();
        const response = await fetch(`/api/schedules/${scheduleId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                enabled: enabled
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Schedule ${enabled ? 'enabled' : 'disabled'} successfully!`);
            loadSchedules();
            loadSchedulerStatus();
        } else {
            showError(result.error || 'Failed to update schedule');
        }
        
    } catch (error) {
        console.error('Error toggling schedule:', error);
        showError('Error updating schedule: ' + error.message);
    }
}

// Authentication and Portfolio Management Functions
let currentUser = null;
let currentPortfolio = null;
let csrfToken = null;

// Get CSRF token
async function getCSRFToken() {
    try {
        console.log('Fetching CSRF token...');
        const response = await fetch('/api/csrf-token');
        console.log('CSRF token response status:', response.status);
        const data = await response.json();
        console.log('CSRF token data:', data);
        csrfToken = data.csrf_token;
        console.log('CSRF token set:', csrfToken ? 'Yes' : 'No');
        return csrfToken;
    } catch (error) {
        console.error('Error getting CSRF token:', error);
        return null;
    }
}

// Check user authentication status
async function checkUserAuthentication() {
    try {
        const response = await fetch('/api/user/profile');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                currentUser = data.data;
                showUserMenu();
                loadPortfolios();
            } else {
                showLoginMenu();
            }
        } else {
            showLoginMenu();
        }
    } catch (error) {
        console.error('Error checking authentication:', error);
        showLoginMenu();
    }
}

function showUserMenu() {
    document.getElementById('userMenu').style.display = 'block';
    document.getElementById('loginMenu').style.display = 'none';
    document.getElementById('userDisplayName').textContent = currentUser.username;
}

function showLoginMenu() {
    document.getElementById('userMenu').style.display = 'none';
    document.getElementById('loginMenu').style.display = 'block';
}

// Tab switching functions
function showPortfolioTab() {
    // Hide all tabs
    document.getElementById('analysisTab').classList.add('d-none');
    document.getElementById('schedulerTab').classList.add('d-none');
    document.getElementById('portfolioTab').classList.remove('d-none');
    
    if (currentUser) {
        loadPortfolios();
    } else {
        showError('Please log in to access portfolio management');
    }
}

// Portfolio Management Functions
async function loadPortfolios() {
    try {
        const response = await fetch('/api/portfolios');
        const data = await response.json();
        
        if (data.success) {
            const portfolios = data.data;
            const portfoliosListEl = document.getElementById('portfoliosList');
            
            if (portfolios.length === 0) {
                portfoliosListEl.innerHTML = `
                    <div class="text-center text-muted">
                        <i class="fas fa-briefcase fa-3x mb-3"></i>
                        <p>No portfolios created yet.</p>
                        <p>Create your first portfolio to start tracking your investments.</p>
                    </div>
                `;
                return;
            }
            
            portfoliosListEl.innerHTML = portfolios.map(portfolio => {
                const summary = portfolio.summary;
                const totalValue = summary.total_value || 0;
                const totalGainLoss = summary.total_gain_loss || 0;
                const gainLossPercent = summary.total_gain_loss_percent || 0;
                
                const gainLossClass = totalGainLoss >= 0 ? 'text-success' : 'text-danger';
                const gainLossIcon = totalGainLoss >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
                
                return `
                    <div class="card mb-3 portfolio-card" onclick="selectPortfolio(${portfolio.id})">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="mb-0">${portfolio.name}</h6>
                                <div>
                                    <button class="btn btn-outline-success btn-sm me-2" onclick="event.stopPropagation(); fetchPortfolioPrices(${portfolio.id})" title="Update Prices">
                                        <i class="fas fa-sync-alt"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="event.stopPropagation(); deletePortfolio(${portfolio.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                            
                            <div class="row mb-2">
                                <div class="col-6">
                                    <small class="text-muted">Total Value</small>
                                    <div class="fw-bold">$${totalValue.toFixed(2)}</div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted">Gain/Loss</small>
                                    <div class="fw-bold ${gainLossClass}">
                                        <i class="fas ${gainLossIcon} me-1"></i>
                                        $${totalGainLoss.toFixed(2)} (${gainLossPercent.toFixed(2)}%)
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-6">
                                    <small class="text-muted">Holdings</small>
                                    <div>${summary.total_holdings || 0}</div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted">Updated</small>
                                    <div>${new Date(portfolio.updated_at).toLocaleDateString()}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading portfolios:', error);
        document.getElementById('portfoliosList').innerHTML = '<p class="text-danger">Error loading portfolios</p>';
    }
}

async function selectPortfolio(portfolioId) {
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}`);
        const data = await response.json();
        
        if (data.success) {
            currentPortfolio = data.data;
            showPortfolioDetails();
        } else {
            showError('Error loading portfolio details');
        }
    } catch (error) {
        console.error('Error selecting portfolio:', error);
        showError('Error loading portfolio details');
    }
}

function showPortfolioDetails() {
    if (!currentPortfolio) return;
    
    document.getElementById('portfolioWelcome').classList.add('d-none');
    document.getElementById('portfolioAnalysis').classList.add('d-none');
    document.getElementById('portfolioDetails').classList.remove('d-none');
    
    // Update portfolio name
    document.getElementById('portfolioDisplayName').textContent = currentPortfolio.name;
    
    // Update portfolio summary
    const summary = currentPortfolio.summary;
    const summaryEl = document.getElementById('portfolioSummary');
    
    summaryEl.innerHTML = `
        <div class="row mb-3">
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Total Value</div>
                    <div class="metric-value">$${(summary.total_value || 0).toFixed(2)}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Total Cost</div>
                    <div class="metric-value">$${(summary.total_cost || 0).toFixed(2)}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Gain/Loss</div>
                    <div class="metric-value ${(summary.total_gain_loss || 0) >= 0 ? 'text-success' : 'text-danger'}">
                        $${(summary.total_gain_loss || 0).toFixed(2)}
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card">
                    <div class="metric-label">Return %</div>
                    <div class="metric-value ${(summary.total_gain_loss_percent || 0) >= 0 ? 'text-success' : 'text-danger'}">
                        ${(summary.total_gain_loss_percent || 0).toFixed(2)}%
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Load holdings
    loadPortfolioHoldings();
}

async function loadPortfolioHoldings() {
    if (!currentPortfolio) return;
    
    try {
        const response = await fetch(`/api/portfolios/${currentPortfolio.id}/holdings`);
        const data = await response.json();
        
        if (data.success) {
            const holdings = data.data;
            const holdingsEl = document.getElementById('portfolioHoldings');
            
            if (holdings.length === 0) {
                holdingsEl.innerHTML = `
                    <div class="text-center text-muted">
                        <i class="fas fa-chart-pie fa-3x mb-3"></i>
                        <p>No holdings in this portfolio yet.</p>
                        <p>Add your first holding to start tracking investments.</p>
                    </div>
                `;
                return;
            }
            
            holdingsEl.innerHTML = `
                <h6>Holdings (${holdings.length})</h6>
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Asset</th>
                                <th>Quantity</th>
                                <th>Avg Cost</th>
                                <th>Current Price</th>
                                <th>Value</th>
                                <th>Gain/Loss</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${holdings.map(holding => {
                                const gainLossClass = holding.gain_loss >= 0 ? 'text-success' : 'text-danger';
                                const gainLossIcon = holding.gain_loss >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
                                
                                return `
                                    <tr>
                                        <td>
                                            <div>
                                                <strong>${holding.asset_symbol}</strong>
                                                <br><small class="text-muted">${holding.asset_name}</small>
                                            </div>
                                        </td>
                                        <td>${holding.quantity.toFixed(6)}</td>
                                        <td>$${holding.avg_cost_per_share.toFixed(4)}</td>
                                        <td>$${holding.current_price ? holding.current_price.toFixed(4) : 'N/A'}</td>
                                        <td>$${holding.current_value.toFixed(2)}</td>
                                        <td class="${gainLossClass}">
                                            <i class="fas ${gainLossIcon} me-1"></i>
                                            $${holding.gain_loss.toFixed(2)} (${holding.gain_loss_percent.toFixed(2)}%)
                                        </td>
                                        <td>
                                            <div class="btn-group" role="group">
                                                <button class="btn btn-outline-primary btn-sm" onclick="analyzeHolding('${holding.asset_symbol}')" title="Analyze">
                                                    <i class="fas fa-chart-line"></i>
                                                </button>
                                                <button class="btn btn-outline-danger btn-sm" onclick="removeHolding('${holding.asset_symbol}')" title="Remove">
                                                    <i class="fas fa-trash"></i>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading holdings:', error);
        document.getElementById('portfolioHoldings').innerHTML = '<p class="text-danger">Error loading holdings</p>';
    }
}

// Modal Functions
function showCreatePortfolioModal() {
    if (!currentUser) {
        showError('Please log in to create portfolios');
        return;
    }
    
    const modalElement = document.getElementById('createPortfolioModal');
    if (!modalElement) {
        showError('Portfolio modal not loaded. Please refresh the page and try again.');
        return;
    }
    
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

function showAddHoldingModal() {
    if (!currentPortfolio) {
        showError('Please select a portfolio first');
        return;
    }
    
    // Populate asset options
    const assetSelect = document.getElementById('holdingAsset');
    assetSelect.innerHTML = '';
    
    // Get all assets with their symbols
    const allAssets = [];
    
    // Add commodities
    if (availableAssets.commodities) {
        availableAssets.commodities.forEach(asset => {
            const symbol = getAssetSymbol(asset, 'commodity');
            if (symbol) {
                allAssets.push({
                    name: asset,
                    symbol: symbol,
                    type: 'commodity'
                });
            }
        });
    }
    
    // Add stocks
    if (availableAssets.stocks) {
        availableAssets.stocks.forEach(asset => {
            const symbol = getAssetSymbol(asset, 'stock');
            if (symbol) {
                allAssets.push({
                    name: asset,
                    symbol: symbol,
                    type: 'stock'
                });
            }
        });
    }
    
    // Sort assets alphabetically
    allAssets.sort((a, b) => a.name.localeCompare(b.name));
    
    // Add options to dropdown
    allAssets.forEach(asset => {
        const option = document.createElement('option');
        option.value = asset.symbol; // Use the proper symbol, not the name
        option.textContent = `${formatAssetName(asset.name)} (${asset.symbol})`;
        assetSelect.appendChild(option);
    });
    
    // Set default date to now
    document.getElementById('holdingDate').value = new Date().toISOString().slice(0, 16);
    
    const modal = new bootstrap.Modal(document.getElementById('addHoldingModal'));
    modal.show();
}

function showProfileModal() {
    if (!currentUser) return;
    
    document.getElementById('profileUsername').value = currentUser.username;
    document.getElementById('profileEmail').value = currentUser.email || '';
    document.getElementById('profileFirstName').value = currentUser.first_name || '';
    document.getElementById('profileLastName').value = currentUser.last_name || '';
    
    const modal = new bootstrap.Modal(document.getElementById('profileModal'));
    modal.show();
}

// Portfolio Actions
async function createPortfolio() {
    if (!currentUser) {
        showError('Please log in to create portfolios');
        return;
    }
    
    const nameElement = document.getElementById('portfolioName');
    const descriptionElement = document.getElementById('portfolioDescription');
    
    if (!nameElement || !descriptionElement) {
        showError('Portfolio form not loaded. Please refresh the page and try again.');
        return;
    }
    
    const name = nameElement.value.trim();
    const description = descriptionElement.value.trim();
    
    if (!name) {
        showError('Portfolio name is required');
        return;
    }
    
    try {
        const token = await getCSRFToken();
        
        const response = await fetch('/api/portfolios', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                name: name,
                description: description
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Portfolio created successfully!');
            bootstrap.Modal.getInstance(document.getElementById('createPortfolioModal')).hide();
            document.getElementById('createPortfolioForm').reset();
            loadPortfolios();
        } else {
            showError(result.error || 'Failed to create portfolio');
        }
    } catch (error) {
        console.error('Error creating portfolio:', error);
        showError('Error creating portfolio: ' + error.message);
    }
}

async function addHolding() {
    if (!currentPortfolio) return;
    
    const asset = document.getElementById('holdingAsset').value;
    const quantity = parseFloat(document.getElementById('holdingQuantity').value);
    const price = parseFloat(document.getElementById('holdingPrice').value);
    const date = document.getElementById('holdingDate').value;
    
    if (!asset || !quantity || !price) {
        showError('Please fill in all required fields');
        return;
    }
    
    try {
        // Get asset name from symbol
        const assetName = getAssetNameFromSymbol(asset);
        const assetType = getAssetTypeFromSymbol(asset);
        
        const token = await getCSRFToken();
        
        const response = await fetch(`/api/portfolios/${currentPortfolio.id}/holdings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                asset_symbol: asset,
                asset_name: formatAssetName(assetName),
                asset_type: assetType,
                quantity: quantity,
                price_per_share: price,
                transaction_date: date ? new Date(date).toISOString() : null
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Holding added successfully!');
            bootstrap.Modal.getInstance(document.getElementById('addHoldingModal')).hide();
            document.getElementById('addHoldingForm').reset();
            selectPortfolio(currentPortfolio.id); // Refresh portfolio details
            loadPortfolios(); // Refresh portfolio list
        } else {
            showError(result.error || 'Failed to add holding');
        }
    } catch (error) {
        console.error('Error adding holding:', error);
        showError('Error adding holding: ' + error.message);
    }
}

async function deletePortfolio(portfolioId) {
    if (!confirm('Are you sure you want to delete this portfolio? This action cannot be undone.')) {
        return;
    }
    
    try {
        const token = await getCSRFToken();
        
        const response = await fetch(`/api/portfolios/${portfolioId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': token
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Portfolio deleted successfully!');
            loadPortfolios();
            if (currentPortfolio && currentPortfolio.id === portfolioId) {
                currentPortfolio = null;
                document.getElementById('portfolioDetails').classList.add('d-none');
                document.getElementById('portfolioWelcome').classList.remove('d-none');
            }
        } else {
            showError(result.error || 'Failed to delete portfolio');
        }
    } catch (error) {
        console.error('Error deleting portfolio:', error);
        showError('Error deleting portfolio: ' + error.message);
    }
}

async function updateProfile() {
    const email = document.getElementById('profileEmail').value;
    const firstName = document.getElementById('profileFirstName').value;
    const lastName = document.getElementById('profileLastName').value;
    
    try {
        const token = await getCSRFToken();
        
        const response = await fetch('/api/user/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                email: email,
                first_name: firstName,
                last_name: lastName
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Profile updated successfully!');
            bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
            currentUser = result.data;
            document.getElementById('userDisplayName').textContent = currentUser.username;
        } else {
            showError(result.error || 'Failed to update profile');
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showError('Error updating profile: ' + error.message);
    }
}

// Portfolio Analysis Functions
async function analyzePortfolio() {
    if (!currentPortfolio) {
        showError('Please select a portfolio first');
        return;
    }
    
    // Show comprehensive analysis instead of basic analysis
    showComprehensiveAnalysis();
}

// Show comprehensive portfolio analysis interface
function showComprehensiveAnalysis() {
    if (!currentPortfolio) {
        showError('Please select a portfolio first');
        return;
    }
    
    document.getElementById('portfolioDetails').classList.add('d-none');
    document.getElementById('portfolioAnalysis').classList.remove('d-none');
    
    // Reset analysis results
    document.getElementById('portfolioAnalysisResults').innerHTML = `
        <div class="text-center text-muted">
            <i class="fas fa-chart-line fa-3x mb-3"></i>
            <p>Click "Run Analysis" to get comprehensive AI-powered portfolio insights</p>
            <p class="small">This will analyze all holdings using real-time market data and sentiment analysis</p>
        </div>
    `;
}

// Run comprehensive portfolio analysis
async function runComprehensiveAnalysis() {
    if (!currentPortfolio) {
        showError('Please select a portfolio first');
        return;
    }
    
    const timeframe = document.getElementById('analysisTimeframe').value;
    
    // Show loading status
    document.getElementById('analysisStatus').classList.remove('d-none');
    document.getElementById('analysisStatusText').textContent = 'Running comprehensive portfolio analysis...';
    
    try {
        const token = await getCSRFToken();
        const response = await fetch(`/api/portfolios/${currentPortfolio.id}/comprehensive-analysis`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                timeframe_days: parseInt(timeframe)
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayComprehensiveAnalysis(data.data);
            showSuccess('Comprehensive portfolio analysis completed!');
        } else {
            showError(data.error || 'Analysis failed');
        }
    } catch (error) {
        console.error('Error running comprehensive analysis:', error);
        showError('Error running analysis: ' + error.message);
    } finally {
        document.getElementById('analysisStatus').classList.add('d-none');
    }
}

// Display comprehensive analysis results
function displayComprehensiveAnalysis(analysisData) {
    const analysisEl = document.getElementById('portfolioAnalysisResults');
    
    if (!analysisData || !analysisData.analysis) {
        analysisEl.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                No analysis data available. Please try again.
            </div>
        `;
        return;
    }
    
    const analysis = analysisData.analysis;
    const portfolioContext = analysisData.portfolio_context;
    const holdingsData = analysisData.holdings_data;
    const sentimentData = analysisData.sentiment_data;
    
    let html = `
        <div class="comprehensive-analysis">
            <!-- Executive Summary -->
            <div class="card mb-4">
                <div class="card-header">
                    <h6><i class="fas fa-crown me-2"></i>Executive Summary</h6>
                </div>
                <div class="card-body">
                    <p class="lead">${analysis.executive_summary || 'Analysis completed successfully.'}</p>
                </div>
            </div>
            
            <!-- Overall Assessment -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-${getHealthColor(analysis.overall_assessment?.portfolio_health)}">
                                ${analysis.overall_assessment?.portfolio_health || 'N/A'}
                            </h5>
                            <p class="card-text small">Portfolio Health</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-${getRiskColor(analysis.overall_assessment?.risk_level)}">
                                ${analysis.overall_assessment?.risk_level || 'N/A'}
                            </h5>
                            <p class="card-text small">Risk Level</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title">${analysis.overall_assessment?.diversification_score || 'N/A'}/100</h5>
                            <p class="card-text small">Diversification Score</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title text-${getGradeColor(analysis.overall_assessment?.performance_rating)}">
                                ${analysis.overall_assessment?.performance_rating || 'N/A'}
                            </h5>
                            <p class="card-text small">Performance Rating</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Key Metrics -->
            <div class="card mb-4">
                <div class="card-header">
                    <h6><i class="fas fa-chart-bar me-2"></i>Key Metrics</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Total Return:</strong> ${analysis.key_metrics?.total_return_percentage || 'N/A'}</p>
                            <p><strong>Best Performer:</strong> ${analysis.key_metrics?.best_performer || 'N/A'}</p>
                            <p><strong>Worst Performer:</strong> ${analysis.key_metrics?.worst_performer || 'N/A'}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Most Volatile:</strong> ${analysis.key_metrics?.most_volatile || 'N/A'}</p>
                            <p><strong>Least Volatile:</strong> ${analysis.key_metrics?.least_volatile || 'N/A'}</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Holdings Analysis -->
            <div class="card mb-4">
                <div class="card-header">
                    <h6><i class="fas fa-list me-2"></i>Holdings Analysis</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6 class="text-success">Strong Holds</h6>
                            <ul class="list-group list-group-flush">
                                ${(analysis.individual_holdings_analysis?.strong_holds || []).map(asset => 
                                    `<li class="list-group-item">${asset}</li>`
                                ).join('')}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6 class="text-warning">Weak Holds</h6>
                            <ul class="list-group list-group-flush">
                                ${(analysis.individual_holdings_analysis?.weak_holds || []).map(asset => 
                                    `<li class="list-group-item">${asset}</li>`
                                ).join('')}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Recommendations -->
            <div class="card mb-4">
                <div class="card-header">
                    <h6><i class="fas fa-lightbulb me-2"></i>Recommendations</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6 class="text-primary">Immediate Actions</h6>
                            <ul class="list-group list-group-flush">
                                ${(analysis.recommendations?.immediate_actions || []).map(action => 
                                    `<li class="list-group-item">${action}</li>`
                                ).join('')}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6 class="text-info">New Investments</h6>
                            <ul class="list-group list-group-flush">
                                ${(analysis.recommendations?.new_investments || []).map(investment => 
                                    `<li class="list-group-item">${investment}</li>`
                                ).join('')}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Detailed Holdings Data -->
            <div class="card mb-4">
                <div class="card-header">
                    <h6><i class="fas fa-table me-2"></i>Detailed Holdings Data</h6>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Asset</th>
                                    <th>Current Price</th>
                                    <th>Price Change</th>
                                    <th>Volatility</th>
                                    <th>Sentiment</th>
                                    <th>News Articles</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${Object.keys(holdingsData).map(symbol => {
                                    const holding = holdingsData[symbol];
                                    const sentiment = sentimentData[symbol];
                                    return `
                                        <tr>
                                            <td><strong>${symbol}</strong></td>
                                            <td>$${holding.current_price?.toFixed(2) || 'N/A'}</td>
                                            <td class="${holding.price_change_percentage >= 0 ? 'text-success' : 'text-danger'}">
                                                ${holding.price_change_percentage?.toFixed(2) || 'N/A'}%
                                            </td>
                                            <td>${holding.volatility?.toFixed(2) || 'N/A'}%</td>
                                            <td>
                                                <span class="badge bg-${getSentimentColor(sentiment?.sentiment_score)}">
                                                    ${sentiment?.sentiment_score?.toFixed(1) || 'N/A'}/100
                                                </span>
                                            </td>
                                            <td>${sentiment?.total_articles || 0}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    analysisEl.innerHTML = html;
}

// Hide portfolio analysis
function hidePortfolioAnalysis() {
    document.getElementById('portfolioAnalysis').classList.add('d-none');
    document.getElementById('portfolioDetails').classList.remove('d-none');
}

// Helper functions for styling
function getHealthColor(health) {
    switch(health) {
        case 'EXCELLENT': return 'success';
        case 'GOOD': return 'primary';
        case 'FAIR': return 'warning';
        case 'POOR': return 'danger';
        default: return 'secondary';
    }
}

function getRiskColor(risk) {
    switch(risk) {
        case 'LOW': return 'success';
        case 'MEDIUM': return 'warning';
        case 'HIGH': return 'danger';
        default: return 'secondary';
    }
}

function getGradeColor(grade) {
    switch(grade) {
        case 'A': return 'success';
        case 'B': return 'primary';
        case 'C': return 'warning';
        case 'D': return 'danger';
        case 'F': return 'danger';
        default: return 'secondary';
    }
}

function getSentimentColor(score) {
    if (score >= 70) return 'success';
    if (score >= 50) return 'warning';
    return 'danger';
}

function showPortfolioAnalysis(analysisData) {
    document.getElementById('portfolioDetails').classList.add('d-none');
    document.getElementById('portfolioAnalysis').classList.remove('d-none');
    
    const analysisEl = document.getElementById('portfolioAnalysisResults');
    
    if (!analysisData || Object.keys(analysisData.analysis_by_asset || {}).length === 0) {
        analysisEl.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-chart-line fa-3x mb-3"></i>
                <p>No analysis available for this portfolio.</p>
                <p>Run analysis on individual holdings to get AI recommendations.</p>
            </div>
        `;
        return;
    }
    
    analysisEl.innerHTML = `
        <h6>AI Analysis Summary</h6>
        <div class="row mb-3">
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-label">Total Holdings</div>
                    <div class="metric-value">${analysisData.total_holdings || 0}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-label">With Analysis</div>
                    <div class="metric-value">${analysisData.holdings_with_analysis || 0}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="metric-card">
                    <div class="metric-label">Coverage</div>
                    <div class="metric-value">${((analysisData.holdings_with_analysis || 0) / (analysisData.total_holdings || 1) * 100).toFixed(1)}%</div>
                </div>
            </div>
        </div>
        
        <h6>Asset Analysis</h6>
        <div class="row">
            ${Object.entries(analysisData.analysis_by_asset || {}).map(([asset, analysis]) => {
                const recommendationClass = analysis.latest_recommendation === 'BUY' ? 'success' : 
                                         analysis.latest_recommendation === 'SELL' ? 'danger' : 'warning';
                
                return `
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <h6 class="mb-0">${asset.toUpperCase()}</h6>
                                    <span class="badge bg-${recommendationClass}">${analysis.latest_recommendation}</span>
                                </div>
                                <p class="mb-2"><strong>Confidence:</strong> ${(analysis.confidence * 100).toFixed(0)}%</p>
                                ${analysis.target_price ? `<p class="mb-2"><strong>Target Price:</strong> $${analysis.target_price.toFixed(4)}</p>` : ''}
                                ${analysis.stop_loss ? `<p class="mb-2"><strong>Stop Loss:</strong> $${analysis.stop_loss.toFixed(4)}</p>` : ''}
                                <p class="small text-muted mb-0">${analysis.reasoning || 'No reasoning available'}</p>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

async function analyzeHolding(assetSymbol) {
    // Show analysis tab and select the asset
    showAnalysisTab();
    selectAsset(assetSymbol);
    
    // Automatically run analysis for this holding
    try {
        showLoading();
        const token = await getCSRFToken();
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            body: JSON.stringify({
                asset: assetSymbol,
                timeframe: 30, // Default timeframe
                send_email: false, // Don't send email for individual holding analysis
                risk_tolerance: 'moderate' // Default risk tolerance
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentAnalysis = result.data;
            displayResults(result.data);
            showSuccess('Analysis completed successfully!');
        } else {
            showError(result.error || 'Analysis failed');
        }
    } catch (error) {
        console.error('Error running analysis:', error);
        showError('Error running analysis: ' + error.message);
    }
}

// Price fetching functions
async function updateAllPrices() {
    if (!currentPortfolio) {
        showError('Please select a portfolio first');
        return;
    }
    
    await fetchPortfolioPrices(currentPortfolio.id);
}

async function fetchPortfolioPrices(portfolioId) {
    try {
        showSuccess('Fetching current prices...');
        
        const response = await fetch(`/api/portfolios/${portfolioId}/fetch-prices`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message);
            // Refresh portfolio details to show updated prices
            if (currentPortfolio && currentPortfolio.id === portfolioId) {
                selectPortfolio(portfolioId);
            }
            // Refresh portfolio list
            loadPortfolios();
        } else {
            showError(result.error || 'Failed to fetch prices');
        }
    } catch (error) {
        console.error('Error fetching prices:', error);
        showError('Error fetching prices: ' + error.message);
    }
}

async function getCurrentPrice(symbol) {
    try {
        const response = await fetch(`/api/prices/${symbol}`);
        const data = await response.json();
        
        if (data.success) {
            return data.current_price;
        } else {
            console.error(`Error fetching price for ${symbol}:`, data.error);
            return null;
        }
    } catch (error) {
        console.error(`Error fetching price for ${symbol}:`, error);
        return null;
    }
}

async function getBatchPrices(symbols) {
    try {
        const response = await fetch('/api/prices/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbols: symbols })
        });
        
        const data = await response.json();
        
        if (data.success) {
            return data.prices;
        } else {
            console.error('Error fetching batch prices:', data.error);
            return {};
        }
    } catch (error) {
        console.error('Error fetching batch prices:', error);
        return {};
    }
}

function exportPortfolio() {
    showSuccess('Export feature coming soon!');
}

async function removeHolding(assetSymbol) {
    if (!currentPortfolio) {
        showError('Please select a portfolio first');
        return;
    }
    
    if (!confirm(`Are you sure you want to remove ${assetSymbol} from this portfolio?`)) {
        return;
    }
    
    try {
        const token = await getCSRFToken();
        
        const response = await fetch(`/api/portfolios/${currentPortfolio.id}/holdings/${assetSymbol}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Holding removed successfully!');
            selectPortfolio(currentPortfolio.id); // Refresh portfolio details
        } else {
            showError(result.error || 'Failed to remove holding');
        }
    } catch (error) {
        console.error('Error removing holding:', error);
        showError('Error removing holding: ' + error.message);
    }
}

function showPortfolioTransactions() {
    showSuccess('Transaction history feature coming soon!');
}
