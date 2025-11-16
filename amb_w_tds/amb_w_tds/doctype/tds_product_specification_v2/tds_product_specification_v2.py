import frappe
from frappe.model.document import Document
import json

class TDSProductSpecificationv2(Document):
    def before_save(self):
        """Auto-update AI analysis when TDS is saved"""
        pass
    
    @frappe.whitelist()
    def analyze_with_ai(self):
        """Analyze this TDS specification using AI and update fields"""
        try:
            from amb_w_tds.ai_functions.biochemical_engine import predict_formulation_quality
            
            # Prepare formulation data from TDS
            formulation_data = {
                "parameters": {
                    "brix": self.target_brix,
                    "solids": self.total_solids,
                    "ph": self._parse_ph_range(self.ph_range) if self.ph_range else None
                },
                "amino_acids": self._get_amino_acid_composition()
            }
            
            # Get AI prediction
            result = predict_formulation_quality(json.dumps(formulation_data))
            analysis = json.loads(result)
            
            # Update TDS fields with AI results
            self.ai_quality_score = analysis.get('quality_score', 0)
            self.ai_confidence = analysis.get('confidence', 0)
            self.ai_risk_factors = ', '.join(analysis.get('risk_factors', []))
            self.ai_recommendations = ' | '.join(analysis.get('recommendations', []))
            
            self.save()
            frappe.db.commit()
            
            frappe.msgprint(f"AI Analysis Complete: Quality Score {self.ai_quality_score}")
            
            return {
                "success": True,
                "quality_score": self.ai_quality_score,
                "confidence": self.ai_confidence,
                "risk_factors": self.ai_risk_factors,
                "recommendations": self.ai_recommendations
            }
            
        except Exception as e:
            frappe.log_error(f"AI Analysis failed for TDS {self.name}: {str(e)}")
            frappe.msgprint(f"AI Analysis failed: {str(e)}", indicator='red')
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_ph_range(self, ph_range):
        """Parse pH range string to get average value"""
        try:
            if ph_range and '-' in ph_range:
                low, high = ph_range.split('-')
                return (float(low.strip()) + float(high.strip())) / 2
            elif ph_range:
                return float(ph_range.strip())
            else:
                return None
        except:
            return None
    
    def _get_amino_acid_composition(self):
        """Get amino acid composition from child table if available"""
        amino_acids = {}
        
        if hasattr(self, 'amino_acid_specifications') and self.amino_acid_specifications:
            for aa in self.amino_acid_specifications:
                if aa.amino_acid and hasattr(aa, 'concentration_ppm') and aa.concentration_ppm:
                    amino_acids[aa.amino_acid] = aa.concentration_ppm
        
        return amino_acids
