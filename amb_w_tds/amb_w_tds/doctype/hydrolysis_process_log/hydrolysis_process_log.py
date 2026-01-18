# Copyright (c) 2026, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class HydrolysisProcessLog(Document):
	def before_save(self):
		"""Calculate derived values before saving"""
		self.calculate_yields()
		self.calculate_solids()
	
	def calculate_yields(self):
		"""Calculate yield percentages for hydrolysis process"""
		penca = flt(self.penca_total_kg)
		bagazo = flt(self.bagazo_kg)
		juice_pressed = flt(self.juice_pressed_liters)
		
		if penca > 0:
			# Yield: Penca to Juice (assuming 1 L juice ≈ 1 kg)
			if juice_pressed > 0:
				self.penca_to_juice_percent = (juice_pressed / penca) * 100
			
			# Yield: Penca to Bagazo
			if bagazo > 0:
				self.penca_to_bagazo_percent = (bagazo / penca) * 100
		
		# Calculate enzyme total
		enzyme_ml_kg = flt(self.enzyme_ml_per_kg)
		if enzyme_ml_kg > 0 and penca > 0:
			self.enzyme_total_ml = enzyme_ml_kg * penca
	
	def calculate_solids(self):
		"""Calculate solid content in kg from volume and percentage"""
		# Pressed solids
		if self.juice_pressed_liters and self.juice_pressed_solids_percent:
			self.juice_pressed_solids_kg = (
				flt(self.juice_pressed_liters) * flt(self.juice_pressed_solids_percent) / 100
			)
		
		# Decolorized solids
		if self.juice_decolorized_liters and self.juice_decolorized_solids_percent:
			self.juice_decolorized_solids_kg = (
				flt(self.juice_decolorized_liters) * flt(self.juice_decolorized_solids_percent) / 100
			)
		
		# Refiltrated solids
		if self.juice_refiltrated_liters and self.juice_refiltrated_solids_percent:
			self.juice_refiltrated_solids_kg = (
				flt(self.juice_refiltrated_liters) * flt(self.juice_refiltrated_solids_percent) / 100
			)
		
		# Final envasado solids
		if self.kilos_envasado and self.final_solids_percent:
			self.final_solids_kg = (flt(self.kilos_envasado) * flt(self.final_solids_percent)
                        )
