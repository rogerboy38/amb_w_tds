/**
 * Market Research Form Script
 * 
 * Client-side JavaScript for enhanced Market Research form
 */

frappe.ui.form.on('Market Research', {
    refresh: function(frm) {
        add_custom_buttons(frm);
        set_form_styling(frm);
        update_progress_indicators(frm);
    },
    
    onload: function(frm) {
        set_field_properties(frm);
        setup_research_tracking(frm);
    },
    
    research_type: function(frm) {
        update_template_suggestions(frm);
    },
    
    country: function(frm) {
        load_market_data(frm);
    },
    
    research_status: function(frm) {
        update_completion_percentage(frm);
    },
    
    completion_percentage: function(frm) {
        update_status_based_on_completion(frm);
    }
});

function add_custom_buttons(frm) {
    if (!frm.doc.__islocal) {
        // Add Generate Report button
        if (frm.doc.research_status === "Completed") {
            frm.add_custom_button(__('Generate Report'), function() {
                generate_market_research_report(frm);
            }, __('Create'));
        }
        
        // Add Create Market Entry Plan button
        if (frm.doc.research_status === "Completed" && frm.doc.strategic_recommendations) {
            frm.add_custom_button(__('Market Entry Plan'), function() {
                create_market_entry_plan_from_research(frm);
            }, __('Create'));
        }
        
        // Add Competitive Analysis button
        frm.add_custom_button(__('Competitive Analysis'), function() {
            show_competitive_analysis(frm);
        }, __('View'));
        
        // Add Market Intelligence button
        frm.add_custom_button(__('Market Intelligence'), function() {
            frappe.call({
                method: "sysmayal.sysmayal.doctype.market_research.market_research.get_market_intelligence_by_country",
                args: {"country": frm.doc.country},
                callback: function(r) {
                    if (r.message) {
                        show_market_intelligence_dialog(r.message);
                    }
                }
            });
        }, __('View'));
        
        // Add Export Research button
        frm.add_custom_button(__('Export Research'), function() {
            export_research_data(frm);
        }, __('Actions'));
        
        // Add Share Research button
        frm.add_custom_button(__('Share Research'), function() {
            share_research_findings(frm);
        }, __('Actions'));
    }
}

function set_form_styling(frm) {
    // Color-code sections based on research status
    if (frm.doc.research_status) {
        let color_map = {
            "Completed": "#d4edda",
            "In Progress": "#cce5ff",
            "Data Collection": "#fff3cd",
            "Analysis": "#e6f3ff",
            "Planning": "#f8f9fa",
            "On Hold": "#f8d7da"
        };
        
        let bg_color = color_map[frm.doc.research_status];
        if (bg_color) {
            frm.form_wrapper.find('.form-page').css('background-color', bg_color);
        }
    }
}

function update_progress_indicators(frm) {
    // Clear existing indicators
    frm.dashboard.clear_headline();
    
    // Add completion percentage indicator
    if (frm.doc.completion_percentage) {
        let color = "red";
        if (frm.doc.completion_percentage >= 80) color = "green";
        else if (frm.doc.completion_percentage >= 60) color = "blue";
        else if (frm.doc.completion_percentage >= 40) color = "orange";
        
        frm.dashboard.add_indicator(
            `Progress: ${frm.doc.completion_percentage}%`,
            color
        );
    }
    
    // Add priority indicator
    if (frm.doc.priority) {
        let priority_colors = {
            'Critical': 'red',
            'High': 'orange',
            'Medium': 'blue',
            'Low': 'green'
        };
        
        frm.dashboard.add_indicator(
            `Priority: ${frm.doc.priority}`,
            priority_colors[frm.doc.priority] || 'gray'
        );
    }
    
    // Add reliability indicator
    if (frm.doc.reliability_score) {
        let reliability_colors = {
            'High': 'green',
            'Medium': 'orange',
            'Low': 'red'
        };
        
        frm.dashboard.add_indicator(
            `Reliability: ${frm.doc.reliability_score}`,
            reliability_colors[frm.doc.reliability_score] || 'gray'
        );
    }
}

function set_field_properties(frm) {
    // Set research lead filter
    frm.set_query('research_lead', function() {
        return {
            filters: {
                'enabled': 1,
                'user_type': 'System User'
            }
        };
    });
    
    // Set country filter for major markets
    frm.set_query('country', function() {
        return {
            filters: {
                'name': ['in', ['United States', 'Canada', 'Germany', 'France', 'United Kingdom', 'Australia', 'Japan', 'Brazil', 'India', 'China']]
            }
        };
    });
}

function setup_research_tracking(frm) {
    // Auto-update fields based on research type
    if (frm.doc.research_type && !frm.doc.research_methods) {
        let method_templates = {
            "Market Analysis": "Market size analysis, competitor research, trend analysis",
            "Competitive Intelligence": "Competitor profiling, market share analysis, SWOT analysis", 
            "Customer Research": "Surveys, focus groups, customer interviews, behavioral analysis",
            "Product Research": "Product testing, feature analysis, pricing research",
            "Industry Analysis": "Industry trends, regulatory analysis, market drivers",
            "Trend Analysis": "Market trend identification, future projections, scenario analysis"
        };
        
        if (method_templates[frm.doc.research_type]) {
            frm.set_value('research_methods', method_templates[frm.doc.research_type]);
        }
    }
}

function update_template_suggestions(frm) {
    if (frm.doc.research_type) {
        let suggestions = get_research_template_suggestions(frm.doc.research_type);
        show_template_suggestions_dialog(frm, suggestions);
    }
}

function get_research_template_suggestions(research_type) {
    let templates = {
        "Market Analysis": {
            focus_areas: ["Market size and growth", "Market segmentation", "Key drivers and barriers", "Regulatory environment"],
            key_questions: ["What is the current market size?", "What are the growth projections?", "Who are the key customer segments?", "What are the main market drivers?"],
            data_sources: ["Industry reports", "Government statistics", "Trade associations", "Market research firms"]
        },
        "Competitive Intelligence": {
            focus_areas: ["Competitor identification", "Market share analysis", "Competitive positioning", "Strengths and weaknesses"],
            key_questions: ["Who are the main competitors?", "What are their market shares?", "What are their competitive advantages?", "What are potential threats?"],
            data_sources: ["Company websites", "Annual reports", "Industry publications", "Customer feedback"]
        },
        "Customer Research": {
            focus_areas: ["Customer demographics", "Buying behavior", "Preferences and needs", "Price sensitivity"],
            key_questions: ["Who are our target customers?", "What drives their purchasing decisions?", "What are their preferences?", "How price sensitive are they?"],
            data_sources: ["Surveys", "Focus groups", "Customer interviews", "Sales data analysis"]
        }
    };
    
    return templates[research_type] || {};
}

function load_market_data(frm) {
    if (frm.doc.country) {
        // Load existing market research for the country
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Market Research",
                filters: {
                    "country": frm.doc.country,
                    "research_status": "Completed",
                    "name": ["!=", frm.doc.name]
                },
                fields: ["name", "research_title", "research_type", "research_date"],
                limit: 5
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    show_existing_research_dialog(r.message);
                }
            }
        });
    }
}

function update_completion_percentage(frm) {
    let percentage_map = {
        "Planning": 10,
        "In Progress": 30,
        "Data Collection": 50,
        "Analysis": 70,
        "Reporting": 90,
        "Completed": 100,
        "On Hold": frm.doc.completion_percentage || 0,
        "Cancelled": 0
    };
    
    if (frm.doc.research_status && !frm.doc.completion_percentage) {
        frm.set_value('completion_percentage', percentage_map[frm.doc.research_status] || 0);
    }
}

function update_status_based_on_completion(frm) {
    if (frm.doc.completion_percentage === 100 && frm.doc.research_status !== "Completed") {
        frm.set_value('research_status', 'Completed');
    } else if (frm.doc.completion_percentage === 0 && frm.doc.research_status !== "Planning") {
        frm.set_value('research_status', 'Planning');
    }
}

function generate_market_research_report(frm) {
    frappe.call({
        method: "sysmayal.sysmayal.doctype.market_research.market_research.generate_market_report",
        args: {"research_name": frm.doc.name},
        callback: function(r) {
            if (r.message) {
                show_report_preview_dialog(r.message);
            }
        }
    });
}

function create_market_entry_plan_from_research(frm) {
    frappe.new_doc('Market Entry Plan', {
        plan_name: `Market Entry - ${frm.doc.country} (${frm.doc.product_category})`,
        target_country: frm.doc.country,
        target_market: frm.doc.region,
        product_category: frm.doc.product_category,
        market_analysis: frm.doc.key_findings,
        competitive_landscape: frm.doc.competitive_landscape,
        market_barriers: frm.doc.market_barriers,
        business_objective: frm.doc.strategic_recommendations,
        risk_assessment: frm.doc.risk_factors,
        reference_research: frm.doc.name
    });
}

function show_competitive_analysis(frm) {
    frappe.call({
        method: "sysmayal.sysmayal.doctype.market_research.market_research.get_competitive_analysis_summary",
        args: {"research_name": frm.doc.name},
        callback: function(r) {
            if (r.message) {
                show_competitive_analysis_dialog(r.message);
            }
        }
    });
}

function export_research_data(frm) {
    frappe.call({
        method: "sysmayal.sysmayal.doctype.market_research.market_research.generate_market_report",
        args: {"research_name": frm.doc.name},
        callback: function(r) {
            if (r.message) {
                // Convert to JSON and download
                let data_str = JSON.stringify(r.message, null, 2);
                let data_uri = 'data:application/json;charset=utf-8,' + encodeURIComponent(data_str);
                
                let export_file_name = `${frm.doc.research_title.replace(/[^a-z0-9]/gi, '_')}_${frappe.datetime.get_today()}.json`;
                
                let link_element = document.createElement('a');
                link_element.setAttribute('href', data_uri);
                link_element.setAttribute('download', export_file_name);
                link_element.click();
                
                frappe.msgprint(__("Research data exported successfully"));
            }
        }
    });
}

function share_research_findings(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __("Share Research Findings"),
        fields: [
            {
                fieldname: "share_with",
                label: __("Share With"),
                fieldtype: "Link",
                options: "User",
                reqd: 1
            },
            {
                fieldname: "include_sections",
                label: __("Include Sections"),
                fieldtype: "MultiSelect",
                options: "Market Overview\\nCompetitive Analysis\\nCustomer Insights\\nSWOT Analysis\\nTrends and Forecasts\\nConclusions",
                default: "Market Overview,Competitive Analysis,Conclusions"
            },
            {
                fieldname: "message",
                label: __("Message"),
                fieldtype: "Text",
                description: __("Optional message to include with the shared research")
            }
        ],
        primary_action_label: __("Share"),
        primary_action: function(values) {
            frappe.call({
                method: "sysmayal.sysmayal.doctype.market_research.market_research.share_research",
                args: {
                    "research_name": frm.doc.name,
                    "share_with": values.share_with,
                    "sections": values.include_sections,
                    "message": values.message
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(__("Research findings shared successfully"));
                        dialog.hide();
                    }
                }
            });
        }
    });
    
    dialog.show();
}

function show_template_suggestions_dialog(frm, suggestions) {
    if (!suggestions || Object.keys(suggestions).length === 0) return;
    
    let html = "<div class='research-suggestions'>";
    
    if (suggestions.focus_areas) {
        html += "<h6>Suggested Focus Areas:</h6><ul>";
        suggestions.focus_areas.forEach(area => {
            html += `<li>${area}</li>`;
        });
        html += "</ul>";
    }
    
    if (suggestions.key_questions) {
        html += "<h6>Key Questions to Address:</h6><ul>";
        suggestions.key_questions.forEach(question => {
            html += `<li>${question}</li>`;
        });
        html += "</ul>";
    }
    
    if (suggestions.data_sources) {
        html += "<h6>Recommended Data Sources:</h6><ul>";
        suggestions.data_sources.forEach(source => {
            html += `<li>${source}</li>`;
        });
        html += "</ul>";
    }
    
    html += "</div>";
    
    frappe.msgprint({
        title: __("Research Template Suggestions"),
        message: html,
        wide: true
    });
}

function show_existing_research_dialog(research_list) {
    let html = "<p>Existing research for this country:</p><ul>";
    
    research_list.forEach(research => {
        html += `<li><strong>${research.research_title}</strong> (${research.research_type}) - ${research.research_date}</li>`;
    });
    
    html += "</ul><p>Consider reviewing these studies to avoid duplication and build upon existing insights.</p>";
    
    frappe.msgprint({
        title: __("Existing Market Research"),
        message: html,
        wide: true
    });
}

function show_report_preview_dialog(report_data) {
    let html = `
        <div class="research-report-preview">
            <h4>${report_data.research_title}</h4>
            <p><strong>Country:</strong> ${report_data.country} | <strong>Category:</strong> ${report_data.product_category}</p>
            
            <h5>Market Overview</h5>
            <p><strong>Market Size:</strong> ${report_data.market_overview.market_size || 'Not specified'}</p>
            <p><strong>Growth Rate:</strong> ${report_data.market_overview.growth_rate || 'Not specified'}</p>
            
            <h5>Key Findings</h5>
            <div>${report_data.conclusions.key_findings || 'No key findings specified'}</div>
            
            <h5>Strategic Recommendations</h5>
            <div>${report_data.conclusions.recommendations || 'No recommendations specified'}</div>
        </div>
    `;
    
    frappe.msgprint({
        title: __("Research Report Preview"),
        message: html,
        wide: true
    });
}

function show_competitive_analysis_dialog(analysis) {
    let html = `
        <div class="competitive-analysis">
            <h5>Competitive Analysis Summary</h5>
            <p><strong>Main Competitors:</strong> ${analysis.main_competitors || 'Not specified'}</p>
            <p><strong>Competitive Threats:</strong> ${analysis.competitive_threats || 'Not specified'}</p>
            <p><strong>Our Advantages:</strong> ${analysis.competitive_advantages || 'Not specified'}</p>
            <p><strong>Market Share Data:</strong> ${analysis.market_share_data || 'Not available'}</p>
        </div>
    `;
    
    frappe.msgprint({
        title: __("Competitive Analysis"),
        message: html,
        wide: true
    });
}

function show_market_intelligence_dialog(intelligence) {
    let html = "<div class='market-intelligence'>";
    
    if (intelligence.message) {
        html += `<p>${intelligence.message}</p>`;
    } else {
        html += `<h5>Market Intelligence for ${intelligence.country}</h5>`;
        html += `<p><strong>Total Research Studies:</strong> ${intelligence.total_research_studies}</p>`;
        
        if (intelligence.market_segments && intelligence.market_segments.length > 0) {
            html += "<p><strong>Market Segments:</strong> " + intelligence.market_segments.join(", ") + "</p>";
        }
        
        if (intelligence.key_competitors && intelligence.key_competitors.length > 0) {
            html += "<p><strong>Key Competitors:</strong> " + intelligence.key_competitors.slice(0, 5).join(", ") + "</p>";
        }
    }
    
    html += "</div>";
    
    frappe.msgprint({
        title: __("Market Intelligence"),
        message: html,
        wide: true
    });
}
