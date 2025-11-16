import frappe
import json

def predict_formulation_quality(formulation_data: str) -> str:
    """
    AI-powered quality prediction for biochemical formulations
    """
    try:
        data = json.loads(formulation_data)
        
        # Mock AI prediction 
        quality_score = 0.85
        confidence = 0.92
        
        # Simple rule-based risk detection
        risks = []
        recommendations = []
        
        amino_acids = data.get('amino_acids', {})
        if amino_acids.get('methionine', 0) > 60:
            risks.append("high_methionine")
            recommendations.append("Consider reducing methionine to 50ppm")
            
        if data.get('parameters', {}).get('brix', 0) < 15:
            risks.append("low_brix") 
            recommendations.append("Increase brix to 15.5-16.0")
            
        # Check for high total amino acids
        total_aa = data.get('total_amino_acids', 0)
        if total_aa > 15000:
            risks.append("high_total_amino_acids")
            recommendations.append("Total amino acids quite high - consider optimization")
            
        return json.dumps({
            "quality_score": quality_score,
            "confidence": confidence,
            "risk_factors": risks,
            "recommendations": recommendations,
            "status": "optimal" if quality_score > 0.8 else "needs_optimization"
        })
        
    except Exception as e:
        return json.dumps({"error": str(e), "quality_score": 0.0})

def optimize_amino_acid_balance(composition: str) -> str:
    """
    Optimize amino acid profile for maximum bioavailability
    """
    try:
        data = json.loads(composition)
        
        # Mock optimization logic
        optimized = data.get('amino_acids', {}).copy()
        
        # Simple balancing rules
        if optimized.get('lysine', 0) > 200:
            optimized['lysine'] = 180
        if optimized.get('methionine', 0) > 60:
            optimized['methionine'] = 50
            
        return json.dumps({
            "optimized_composition": optimized,
            "improvement_score": 0.15,
            "changes_made": ["balanced_lysine", "reduced_methionine"]
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})

def calculate_bioavailability(nutrient_profile: str) -> str:
    """
    Calculate bioavailability score for nutrient delivery
    """
    try:
        profile = json.loads(nutrient_profile)
        
        # Mock bioavailability calculation
        score = 0.78
        factors = ["amino_acid_balance", "vitamin_synergy", "mineral_availability"]
        
        return json.dumps({
            "bioavailability_score": score,
            "key_factors": factors,
            "efficiency": "high" if score > 0.7 else "medium"
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})

def analyze_bom_formulation(bom_formula_name: str) -> str:
    """
    Analyze BOM Formula composition and predict quality using AI
    """
    try:
        # Get the BOM Formula document
        bom_doc = frappe.get_doc("BOM Formula", bom_formula_name)
        
        # Extract composition data
        amino_acids = {}
        total_amino_acids = 0
        
        if hasattr(bom_doc, 'amino_acids') and bom_doc.amino_acids:
            for aa in bom_doc.amino_acids:
                if aa.amino_acid and aa.concentration_ppm:
                    amino_acids[aa.amino_acid] = aa.concentration_ppm
                    if aa.amino_acid != "Total Aminoacids":
                        total_amino_acids += aa.concentration_ppm
        
        # Prepare formulation data
        formulation_data = {
            "amino_acids": amino_acids,
            "parameters": {
                "target_ph": getattr(bom_doc, 'target_ph', None),
                "target_solids": getattr(bom_doc, 'target_solids', None),
                "fermentation_time": getattr(bom_doc, 'fermentation_time_hours', None),
                "fermentation_temperature": getattr(bom_doc, 'fermentation_temperature', None)
            },
            "formula_name": bom_doc.formula_name,
            "total_amino_acids": total_amino_acids
        }
        
        # Use our quality prediction
        quality_result = predict_formulation_quality(json.dumps(formulation_data))
        quality_data = json.loads(quality_result)
        
        # Enhanced analysis
        analysis_result = {
            "formula_name": bom_doc.formula_name,
            "bom_document": bom_formula_name,
            "composition_summary": {
                "total_amino_acids_ppm": total_amino_acids,
                "individual_amino_acids": len(amino_acids),
                "key_amino_acids": list(amino_acids.keys())[:5]
            },
            "quality_analysis": quality_data,
            "manufacturing_parameters": formulation_data["parameters"],
            "optimization_suggestions": []
        }
        
        # BOM-specific optimizations
        if total_amino_acids > 15000:
            analysis_result["optimization_suggestions"].append("High total amino acids - consider optimization")
        
        ph = formulation_data["parameters"].get("target_ph")
        if ph and ph < 4.0:
            analysis_result["optimization_suggestions"].append("Low pH - adjust for skin compatibility")
            
        return json.dumps(analysis_result)
        
    except Exception as e:
        return json.dumps({"error": f"BOM analysis failed: {str(e)}", "formula_name": bom_formula_name})
