 
// =============================================================================
// ENHANCED BATCH NAVBAR WIDGET - Optimized API Calls
// =============================================================================

frappe.provide('frappe.ui');
frappe.provide('amb.batch_widget');

// Initialize when page loads
$(document).ready(function() {
    initializeBatchWidget();
});

// Enhanced Configuration
amb.batch_widget.config = {
    refreshInterval: 300000, // 5 minutes (300,000 ms)
    autoMinimizeDelay: 120000, // 2 minutes
    widgetWidth: 500,
    maxRetries: 3,
    retryDelay: 10000, // 10 seconds
    cacheDuration: 120000, // 2 minutes cache
    plantColors: {
        '1': '#3498db', '2': '#e74c3c', '3': '#2ecc71', '4': '#f39c12', '5': '#9b59b6'
    },
    companyColors: {
        'AMB-Wellness': '#1abc9c', 'Juice': '#3498db', 'Dry Plant Company': '#e74c3c'
    }
};

// State management
amb.batch_widget.state = {
    isFetching: false,
    retryCount: 0,
    lastFetchTime: null,
    cache: null,
    cacheTimestamp: null,
    refreshTimer: null,
    isOnline: true
};

function initializeBatchWidget() {
    if (frappe.session && frappe.session.user !== 'Guest') {
        console.log('🚀 Initializing Enhanced Batch Navbar Widget...');
        
        // Wait for Frappe to fully initialize
        setTimeout(function() {
            // Set up optimized refresh
            setupSmartRefresh();
            
            // Initial load with delay to avoid startup congestion
            setTimeout(update_batch_announcements, 2000);
            
            // Add global refresh button
            addGlobalRefreshButton();
            
            // Set up connectivity monitoring
            setupConnectivityMonitoring();
        }, 3000);
    }
}

// =============================================================================
// ENHANCED API CALL MANAGEMENT
// =============================================================================

function setupSmartRefresh() {
    // Clear any existing timer
    if (amb.batch_widget.state.refreshTimer) {
        clearInterval(amb.batch_widget.state.refreshTimer);
    }
    
    // Smart refresh based on visibility and activity
    amb.batch_widget.state.refreshTimer = setInterval(function() {
        // Only refresh if page is visible and user is active
        if (!document.hidden && amb.batch_widget.state.isOnline) {
            update_batch_announcements();
        }
    }, amb.batch_widget.config.refreshInterval);
    
    // Refresh when page becomes visible
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && !amb.batch_widget.state.isFetching) {
            // If cache is stale, refresh immediately
            const cacheAge = Date.now() - (amb.batch_widget.state.cacheTimestamp || 0);
            if (!amb.batch_widget.state.cache || cacheAge > amb.batch_widget.config.cacheDuration) {
                update_batch_announcements();
            } else {
                // Use cached data if fresh
                display_cached_data();
            }
        }
    });
}

function update_batch_announcements() {
    // Prevent multiple simultaneous calls
    if (amb.batch_widget.state.isFetching) {
        console.log('⏳ API call already in progress, skipping...');
        return;
    }
    
    // Check cache first
    const cacheAge = Date.now() - (amb.batch_widget.state.cacheTimestamp || 0);
    if (amb.batch_widget.state.cache && cacheAge < 30000) { // 30 seconds cache
        console.log('♻️ Using cached data (fresh)');
        display_cached_data();
        return;
    }
    
    console.log('🔄 Fetching Batch AMB data...');
    amb.batch_widget.state.isFetching = true;
    amb.batch_widget.state.lastFetchTime = Date.now();
    
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.get_running_batch_announcements',
        args: {
            include_companies: true,
            include_plants: true,
            include_quality: true
        },
        callback: function(r) {
            amb.batch_widget.state.isFetching = false;
            amb.batch_widget.state.retryCount = 0; // Reset retry counter on success
            
            if (r.message && r.message.success) {
                console.log('✅ API call successful');
                
                // Cache the successful response
                amb.batch_widget.state.cache = r.message;
                amb.batch_widget.state.cacheTimestamp = Date.now();
                
                process_api_response(r.message);
            } else {
                console.warn('⚠️ API returned unsuccessful response:', r.message);
                handle_api_error(r.message || {error: 'Unknown API error'});
            }
        },
        error: function(r) {
            amb.batch_widget.state.isFetching = false;
            console.error('❌ API call failed:', r);
            handle_api_error(r);
        },
        freeze: true,
        freeze_message: __('Refreshing batch data...')
    });
}

function process_api_response(response) {
    if (!response) {
        show_error_message('No data received from server');
        return;
    }
    
    try {
        if (response.grouped_announcements && Object.keys(response.grouped_announcements).length > 0) {
            display_grouped_batch_announcements(response.grouped_announcements, response.stats);
        } else if (response.announcements && response.announcements.length > 0) {
            display_batch_announcements(response.announcements, response.stats);
        } else {
            show_no_batches_message(response.message);
        }
        
        // Update last update time in widget
        update_last_refresh_time();
        
    } catch (error) {
        console.error('Error processing API response:', error);
        show_error_message('Error displaying batch data');
    }
}

function handle_api_error(error) {
    const errorMsg = error.error || error.message || 'Connection failed';
    console.error('API Error:', errorMsg);
    
    // Increment retry counter
    amb.batch_widget.state.retryCount++;
    
    if (amb.batch_widget.state.retryCount <= amb.batch_widget.config.maxRetries) {
        console.log(`🔄 Retrying in ${amb.batch_widget.config.retryDelay/1000} seconds... (Attempt ${amb.batch_widget.state.retryCount}/${amb.batch_widget.config.maxRetries})`);
        
        // Exponential backoff
        const backoffDelay = amb.batch_widget.config.retryDelay * Math.pow(1.5, amb.batch_widget.state.retryCount - 1);
        
        setTimeout(function() {
            if (amb.batch_widget.state.isOnline) {
                update_batch_announcements();
            }
        }, backoffDelay);
        
        show_retry_message(errorMsg, amb.batch_widget.state.retryCount);
    } else {
        console.error('❌ Max retries reached, giving up');
        show_error_message(`Failed to load batches: ${errorMsg}`);
        amb.batch_widget.state.retryCount = 0; // Reset for next attempt
    }
}

function display_cached_data() {
    if (amb.batch_widget.state.cache) {
        console.log('📦 Displaying cached data');
        process_api_response(amb.batch_widget.state.cache);
    }
}

// =============================================================================
// ENHANCED DISPLAY FUNCTIONS
// =============================================================================

function display_grouped_batch_announcements(groupedData, stats = {}) {
    if (!groupedData || Object.keys(groupedData).length === 0) {
        show_no_batches_message();
        return;
    }
    
    let announcement_html = '';
    let totalBatches = stats.total || 0;
    
    try {
        // Process by company
        for (const [companyName, companyData] of Object.entries(groupedData)) {
            const companyColor = amb.batch_widget.config.companyColors[companyName] || '#7f8c8d';
            let companyBatches = 0;
            
            announcement_html += `
                <div class="company-group" style="margin-bottom: 15px;">
                    <div class="company-header" style="
                        display: flex; 
                        align-items: center; 
                        padding: 8px 12px;
                        background: ${companyColor};
                        color: white;
                        border-radius: 5px;
                        margin-bottom: 10px;
                        font-weight: bold;
                    ">
                        <span style="margin-right: 8px;">🏢</span>
                        ${companyName}
                    </div>
            `;
            
            // Process by plant
            for (const [plantCode, plantBatches] of Object.entries(companyData)) {
                const plantColor = amb.batch_widget.config.plantColors[plantCode] || '#95a5a6';
                const plantName = getPlantName(plantCode);
                
                announcement_html += `
                    <div class="plant-group" style="margin-left: 10px; margin-bottom: 12px;">
                        <div class="plant-header" style="
                            display: flex; 
                            align-items: center; 
                            padding: 6px 10px;
                            background: ${plantColor}22;
                            border-left: 4px solid ${plantColor};
                            border-radius: 3px;
                            margin-bottom: 8px;
                            font-size: 13px;
                        ">
                            <span style="margin-right: 6px;">${getPlantIcon(plantCode)}</span>
                            ${plantName} (Plant ${plantCode})
                        </div>
                        <div class="batch-list">
                `;
                
                // Process batches
                if (Array.isArray(plantBatches)) {
                    plantBatches.forEach(function(batch, index) {
                        companyBatches++;
                        
                        const priorityColor = getPriorityColor(batch.priority);
                        const statusIcon = getStatusIcon(batch.quality_status);
                        
                        announcement_html += create_batch_item_html(batch, priorityColor, statusIcon);
                    });
                }
                
                announcement_html += `
                        </div>
                    </div>
                `;
            }
            
            // Update company header with count
            announcement_html = announcement_html.replace(`${companyName}`, `${companyName} <span style="font-size: 0.8em; opacity: 0.9;">(${companyBatches})</span>`);
            
            announcement_html += `</div>`;
        }
        
        if (announcement_html) {
            show_navbar_widget(announcement_html, totalBatches, stats);
        }
        
    } catch (error) {
        console.error('Error displaying grouped batches:', error);
        show_error_message('Error displaying batch data');
    }
}

function create_batch_item_html(batch, priorityColor, statusIcon) {
    return `
        <div class="batch-announcement-item" style="
            margin-bottom: 10px; 
            padding: 10px; 
            background: #f8f9fa; 
            border-radius: 5px;
            border-left: 4px solid ${priorityColor};
            font-family: 'Courier New', monospace;
            position: relative;
            cursor: pointer;
        " onclick="openBatchRecord('${batch.name}')">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <div style="font-weight: bold; margin-bottom: 5px; font-size: 13px; color: #2c3e50;">
                        ${statusIcon} ${batch.title || 'Batch'} - ${batch.batch_code || ''}
                    </div>
                    <div style="font-size: 11px; color: #34495e; margin-bottom: 5px;">
                        Item: ${batch.item_code || 'N/A'} | Level: ${batch.level || 'N/A'}
                    </div>
                    <pre style="
                        margin: 0; 
                        font-size: 11px; 
                        white-space: pre-line; 
                        line-height: 1.3;
                        font-family: inherit;
                        color: #7f8c8d;
                    ">${batch.content || batch.message || 'No details available'}</pre>
                </div>
                <div style="
                    background: rgba(0,0,0,0.05);
                    padding: 3px 6px;
                    border-radius: 3px;
                    font-size: 9px;
                    white-space: nowrap;
                    margin-left: 8px;
                ">
                    ${batch.quality_status || 'Pending'}
                </div>
            </div>
            <div style="
                position: absolute;
                top: 8px;
                right: 8px;
                background: rgba(0,0,0,0.1);
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 9px;
            ">
                ${formatTime(batch.modified || batch.creation)}
            </div>
        </div>
    `;
}

// =============================================================================
// ENHANCED WIDGET MANAGEMENT
// =============================================================================

function show_navbar_widget(html_content, count, stats = {}) {
    // Remove existing widget
    $('.batch-announcement-widget').remove();
    
    const statsHtml = stats.total ? `
        <div style="display: flex; justify-content: space-around; margin: 10px 0; padding: 8px; background: #f8f9fa; border-radius: 5px;">
            <div style="text-align: center;">
                <div style="font-weight: bold; color: #e74c3c;">${stats.high_priority || 0}</div>
                <div style="font-size: 9px;">High Priority</div>
            </div>
            <div style="text-align: center;">
                <div style="font-weight: bold; color: #f39c12;">${stats.quality_check || 0}</div>
                <div style="font-size: 9px;">Quality Check</div>
            </div>
            <div style="text-align: center;">
                <div style="font-weight: bold; color: #3498db;">${stats.container_level || 0}</div>
                <div style="font-size: 9px;">Container Level</div>
            </div>
        </div>
    ` : '';
    
    let widget = $(`
        <div class="batch-announcement-widget" style="
            position: fixed;
            top: 70px;
            right: 20px;
            width: ${amb.batch_widget.config.widgetWidth}px;
            max-height: 70vh;
            overflow-y: auto;
            z-index: 1050;
            background: white;
            border: 2px solid #28a745;
            border-radius: 8px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
            padding: 15px;
            animation: slideInRight 0.5s ease-out;
        ">
            <div style="
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #28a745;
                position: sticky;
                top: 0;
                background: white;
                z-index: 10;
            ">
                <div>
                    <h4 style="margin: 0; color: #28a745; font-size: 16px;">
                        🏭 Production Monitor
                    </h4>
                    <small style="color: #666; font-size: 11px;">
                        ${count} active batch${count !== 1 ? 'es' : ''}
                    </small>
                </div>
                <div>
                    <button class="btn btn-xs btn-success refresh-announcements" style="margin-right: 5px;" title="Refresh Now">
                        🔄
                    </button>
                    <button class="btn btn-xs btn-info toggle-stats" title="Toggle Stats">
                        📊
                    </button>
                    <button class="btn btn-xs btn-secondary minimize-announcement" title="Minimize">
                        📌
                    </button>
                    <button class="btn btn-xs btn-danger close-announcement" title="Close for 1 hour">
                        ✕
                    </button>
                </div>
            </div>
            ${statsHtml}
            <div class="announcement-content">
                ${html_content}
            </div>
            <div style="
                text-align: center; 
                margin-top: 15px; 
                padding-top: 10px;
                border-top: 1px solid #eee;
                font-size: 10px; 
                color: #666;
                position: sticky;
                bottom: 0;
                background: white;
            ">
                🔄 Auto-update every 5 min • 
                <span id="last-update-time">${new Date().toLocaleTimeString()}</span>
            </div>
        </div>
    `);
    
    $('body').append(widget);
    setup_widget_events(widget);
    
    // Auto-minimize after delay
    setTimeout(function() {
        if (widget.is(':visible') && !widget.is(':hover')) {
            minimizeWidget(widget);
        }
    }, amb.batch_widget.config.autoMinimizeDelay);
}

// =============================================================================
// CONNECTIVITY & ERROR HANDLING
// =============================================================================

function setupConnectivityMonitoring() {
    // Online/offline detection
    window.addEventListener('online', function() {
        amb.batch_widget.state.isOnline = true;
        console.log('🌐 Connection restored');
        update_batch_announcements(); // Refresh data when back online
    });
    
    window.addEventListener('offline', function() {
        amb.batch_widget.state.isOnline = false;
        console.warn('🔴 Connection lost');
        show_offline_message();
    });
}

function show_retry_message(errorMsg, retryCount) {
    const widget = $('.batch-announcement-widget');
    if (widget.length) {
        const retryHtml = `
            <div style="
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 8px;
                margin: 10px 0;
                font-size: 11px;
                color: #856404;
            ">
                ⚠️ ${errorMsg}<br>
                Retrying... (${retryCount}/${amb.batch_widget.config.maxRetries})
            </div>
        `;
        widget.find('.announcement-content').prepend(retryHtml);
    }
}

function show_error_message(message) {
    const errorHtml = `
        <div style="
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            font-size: 12px;
            color: #721c24;
        ">
            ❌ ${message}
        </div>
    `;
    
    const widget = $('.batch-announcement-widget');
    if (widget.length) {
        widget.find('.announcement-content').html(errorHtml);
    } else {
        show_navbar_widget(errorHtml, 0);
    }
}

function show_offline_message() {
    const offlineHtml = `
        <div style="
            background: #f8f9fa;
            border: 1px solid #6c757d;
            border-radius: 5px;
            padding: 15px;
            text-align: center;
            color: #6c757d;
        ">
            🔴 Offline<br>
            <small>Batch data will refresh when connection is restored</small>
        </div>
    `;
    
    const widget = $('.batch-announcement-widget');
    if (widget.length) {
        widget.find('.announcement-content').html(offlineHtml);
    }
}

function show_no_batches_message(message = 'No active batches found') {
    const noBatchesHtml = `
        <div style="
            background: #e9ecef;
            border-radius: 5px;
            padding: 20px;
            text-align: center;
            color: #6c757d;
        ">
            📭 ${message}
        </div>
    `;
    
    show_navbar_widget(noBatchesHtml, 0);
}

function update_last_refresh_time() {
    $('#last-update-time').text(new Date().toLocaleTimeString());
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function getPriorityColor(priority) {
    const colors = {
        'high': '#e74c3c',
        'medium': '#f39c12', 
        'low': '#3498db'
    };
    return colors[priority] || '#95a5a6';
}

function getPlantName(plantCode) {
    const plantNames = {
        '1': 'Main Production',
        '2': 'Secondary Plant',
        '3': 'Processing Unit',
        '4': 'Quality Lab',
        '5': 'Packaging Unit'
    };
    return plantNames[plantCode] || 'Plant ' + plantCode;
}

function getPlantIcon(plantCode) {
    const icons = {
        '1': '🏭',
        '2': '🏢',
        '3': '⚙️',
        '4': '🔬',
        '5': '📦'
    };
    return icons[plantCode] || '🏭';
}

function getStatusIcon(quality_status) {
    const icons = {
        'Pending': '📝',
        'In Progress': '⏳',
        'Running': '▶️',
        'Completed': '✅',
        'On Hold': '⏸️',
        'Cancelled': '❌',
        'Quality Check': '🔬',
        'Passed': '✅',
        'Failed': '❌'
    };
    return icons[quality_status] || '📋';
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
}

function openBatchRecord(batchName) {
    if (batchName) {
        frappe.set_route('Form', 'Batch AMB', batchName);
    }
}

function setup_widget_events(widget) {
    // Refresh button
    widget.find('.refresh-announcements').on('click', function() {
        update_batch_announcements();
    });
    
    // Close button
    widget.find('.close-announcement').on('click', function() {
        widget.fadeOut(300, function() {
            $(this).remove();
        });
    });
    
    // Minimize button
    widget.find('.minimize-announcement').on('click', function() {
        minimizeWidget(widget);
    });
    
    // Toggle stats
    widget.find('.toggle-stats').on('click', function() {
        widget.find('.statsHtml').toggle();
    });
}

function minimizeWidget(widget) {
    widget.css({
        'height': '50px',
        'overflow': 'hidden'
    });
    widget.find('.announcement-content').hide();
    
    // Add maximize button
    if (!widget.find('.maximize-btn').length) {
        widget.find('.minimize-announcement').after(
            '<button class="btn btn-xs btn-primary maximize-btn" title="Maximize">⬆️</button>'
        );
        
        widget.find('.maximize-btn').on('click', function() {
            widget.css({
                'height': 'auto',
                'overflow-y': 'auto'
            });
            widget.find('.announcement-content').show();
            $(this).remove();
        });
    }
}

function addGlobalRefreshButton() {
    // Add a small refresh button to navbar (optional)
    if ($('.navbar-batch-refresh').length === 0) {
        $('.navbar-right').prepend(`
            <li class="navbar-batch-refresh">
                <a href="#" onclick="window.refresh_batch_announcements(); return false;" title="Refresh Batches">
                    🔄
                </a>
            </li>
        `);
    }
}

function display_batch_announcements(announcements, stats) {
    // Fallback display for non-grouped data
    let html = '';
    
    announcements.forEach(function(batch) {
        const priorityColor = getPriorityColor(batch.priority);
        const statusIcon = getStatusIcon(batch.quality_status);
        html += create_batch_item_html(batch, priorityColor, statusIcon);
    });
    
    if (html) {
        show_navbar_widget(html, announcements.length, stats);
    }
}

// =============================================================================
// GLOBAL EXPORTS
// =============================================================================

// Make functions available globally with enhanced error handling
window.refresh_batch_announcements = function() {
    console.log('🔄 Manual refresh triggered');
    update_batch_announcements();
};

window.hide_batch_widget = function() {
    $('.batch-announcement-widget').fadeOut(300, function() {
        $(this).remove();
    });
};

window.show_batch_widget = function() {
    if ($('.batch-announcement-widget').length === 0) {
        update_batch_announcements();
    } else {
        $('.batch-announcement-widget').fadeIn();
    }
};

// Cleanup on page unload
$(window).on('beforeunload', function() {
    if (amb.batch_widget.state.refreshTimer) {
        clearInterval(amb.batch_widget.state.refreshTimer);
    }
});

console.log('✅ Enhanced Batch Widget API Manager loaded');
