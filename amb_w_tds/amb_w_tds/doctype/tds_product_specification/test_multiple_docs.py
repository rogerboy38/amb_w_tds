import frappe

print("Testing multiple TDS Product Specification documents...")

# Get 5 documents
docs = frappe.get_all("TDS Product Specification", 
                     fields=["name", "version"],
                     limit=5)

success_count = 0
fail_count = 0

for doc_info in docs:
    try:
        doc = frappe.get_doc("TDS Product Specification", doc_info.name)
        before = doc.version
        doc.save()
        doc.reload()
        after = doc.version
        
        print(f"  ✓ {doc.name}: saved successfully (version: {before})")
        success_count += 1
        
    except AttributeError as e:
        print(f"  ✗ {doc.name}: AttributeError - {e}")
        fail_count += 1
    except Exception as e:
        print(f"  ✗ {doc.name}: {type(e).__name__} - {e}")
        fail_count += 1

print(f"\nResults: {success_count} successful, {fail_count} failed")
if fail_count == 0:
    print("✅ ALL TESTS PASSED!")
else:
    print("⚠️ Some tests failed")
