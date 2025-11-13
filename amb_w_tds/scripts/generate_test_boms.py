"""
Console script to generate test BOMs for web product codes
Execute: bench --site [sitename] execute amb_w_tds.scripts.generate_test_boms.run
"""

import frappe
from amb_w_tds.services.template_bom_service import TemplateBOMService

def run():
    """Main execution function"""
    print("\n" + "="*80)
    print("TEST BOM GENERATION FOR CODIGOS WEB")
    print("="*80 + "\n")
    
    service = TemplateBOMService()
    web_codes = service._get_web_product_codes()
    
    print(f"Total product codes to process: {len(web_codes)}\n")
    print("Product codes:")
    for i, code in enumerate(web_codes, 1):
        print(f"  {i:2d}. {code}")
    
    print("\n" + "="*80)
    print("Proceeding with BOM generation...\n")
    
    results = service.generate_test_boms_for_web_codes()
    
    # Print results
    print("\n" + "="*80)
    print("GENERATION RESULTS")
    print("="*80 + "\n")
    
    print(f"✓ Successfully generated: {len(results['success'])}")
    for item in results['success']:
        print(f"  - {item['code']}: {item['bom']}")
    
    if results['failed']:
        print(f"\n✗ Failed: {len(results['failed'])}")
        for item in results['failed']:
            print(f"  - {item['code']}: {item['error']}")
    
    if results['skipped']:
        print(f"\n⊘ Skipped: {len(results['skipped'])}")
        for item in results['skipped']:
            print(f"  - {item['code']}: {item['reason']}")
    
    print("\n" + "="*80)
    print("VALIDATION PHASE")
    print("="*80 + "\n")
    
    # Validate generated BOMs
    if results['success']:
        print("Validating generated BOMs...\n")
        valid_count = 0
        invalid_count = 0
        
        for item in results['success']:
            try:
                validation = service.validate_generated_bom(item['bom'])
                status = "✓ VALID" if validation['valid'] else "✗ INVALID"
                cost = validation.get('total_cost', 0)
                print(f"{status} - {item['code']}: {item['bom']} (Cost: ${cost:.2f})")
                
                if validation['valid']:
                    valid_count += 1
                else:
                    invalid_count += 1
                    for issue in validation['issues']:
                        print(f"    Issue: {issue}")
                        
            except Exception as e:
                print(f"✗ Validation error for {item['bom']}: {str(e)}")
                invalid_count += 1
        
        print(f"\nValidation Summary: {valid_count} valid, {invalid_count} invalid")
    
    print("\n" + "="*80)
    print("OPERATION COMPLETED")
    print("="*80 + "\n")
    
    # Summary
    total = len(web_codes)
    success = len(results['success'])
    failed = len(results['failed'])
    skipped = len(results['skipped'])
    
    print(f"Total: {total} | Success: {success} | Failed: {failed} | Skipped: {skipped}")
    
    if success == total:
        print("\n🎉 ALL BOMs GENERATED SUCCESSFULLY!")
    elif success > 0:
        print(f"\n✓ {success}/{total} BOMs generated successfully")
    else:
        print("\n⚠ No BOMs were generated")
    
    print()
    
    return results

if __name__ == "__main__":
    run()
