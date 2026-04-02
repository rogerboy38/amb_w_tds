"""
PH12.3 Validation Script - Batch AMB Commands
Run with: bench execute tmp.test_ph12_3.validate
"""
import frappe
import json

def validate():
    results = []
    
    def log_test(test_id, name, passed, details=""):
        status = "PASS" if passed else "FAIL"
        results.append((test_id, status))
        print(f"  [{status}] {test_id}: {name}" + (f" | {details}" if details else ""))
    
    print("=" * 60)
    print("PH12.3 VALIDATION - Batch AMB Commands")
    print("=" * 60)
    
    from raven_ai_agent.api.handlers.batch_amb import BatchAMBMixin
    from raven_ai_agent.api.agent import RaymondLucyAgent
    
    # Get agent instance
    agent = RaymondLucyAgent("Administrator")
    
    # T3.1: All 11 handler methods exist
    methods = [
        '_handle_batch_commands',
        '_handle_batch_help',
        '_handle_batch_create',
        '_handle_batch_sublot',
        '_handle_batch_container',
        '_handle_batch_serial',
        '_handle_batch_weigh',
        '_handle_batch_status',
        '_handle_batch_list',
        '_handle_batch_tree',
        '_handle_batch_pipeline'
    ]
    missing = [m for m in methods if not hasattr(BatchAMBMixin, m)]
    log_test("T3.1", "All 11 handler methods exist", len(missing) == 0, str(missing) if missing else "OK")
    
    # T3.2: batch help returns valid response
    result = agent._handle_batch_commands("batch help", "batch help", False)
    log_test("T3.2", "batch help returns valid response", 
             result and 'Batch AMB Commands' in result.get('message',''), 
             result.get('message','')[:50] if result else "No result")
    
    # T3.3: batch list returns response
    result = agent._handle_batch_commands("batch list", "batch list", False)
    log_test("T3.3", "batch list returns response", 
             result and result.get('message'), 
             result.get('message','')[:50] if result else "No result")
    
    # Get a real batch for testing
    b = frappe.get_all("Batch AMB", limit=1, pluck="name")
    
    # T3.4: batch status with real batch
    if b:
        result = agent._handle_batch_commands(f"batch status {b[0]}", f"batch status {b[0]}", False)
        log_test("T3.4", f"batch status {b[0]}", 
                 result and result.get('message'), 
                 result.get('message','')[:50] if result else "No result")
    else:
        log_test("T3.4", "batch status (no batches)", False, "SKIP - no batches")
    
    # T3.5: batch tree with real batch
    if b:
        result = agent._handle_batch_commands(f"batch tree {b[0]}", f"batch tree {b[0]}", False)
        log_test("T3.5", f"batch tree {b[0]}", 
                 result and result.get('message'), 
                 result.get('message','')[:50] if result else "No result")
    else:
        log_test("T3.5", "batch tree (no batches)", False, "SKIP - no batches")
    
    # T3.6: invalid command handling
    result = agent._handle_batch_commands("batch invalid_xyz", "batch invalid_xyz", False)
    log_test("T3.6", "invalid command returns None", result is None, str(type(result)))
    
    # T3.7: batch list with level filter
    result = agent._handle_batch_commands("batch list 1", "batch list 1", False)
    log_test("T3.7", "batch list level 1", 
             result and result.get('message'), 
             result.get('message','')[:50] if result else "No result")
    
    # T3.8: batch list with status filter
    result = agent._handle_batch_commands("batch list 1 Draft", "batch list 1 draft", False)
    log_test("T3.8", "batch list level 1 Draft", 
             result and result.get('message'), 
             result.get('message','')[:50] if result else "No result")
    
    # T3.9: pipeline with invalid batch returns error
    result = agent._handle_batch_commands("batch pipeline NONEXISTENT In Production", "batch pipeline nonexistent in production", False)
    err_ok = result and ('not found' in result.get('message','').lower() or 'not found' in result.get('error','').lower() or 'error' in result.get('message','').lower() or 'error' in result.get('error','').lower())
    log_test("T3.9", "pipeline invalid batch error", err_ok, str(result)[:50] if result else "No result")
    
    # T3.10: CommandRouter dispatches batch commands
    from raven_ai_agent.api.command_router import CommandRouterMixin
    log_test("T3.10", "CommandRouterMixin has batch handler", 
             hasattr(CommandRouterMixin, '_handle_batch_commands'), 
             "OK" if hasattr(CommandRouterMixin, '_handle_batch_commands') else "Missing")
    
    # Summary
    passed = sum(1 for r in results if r[1] == "PASS")
    total = len(results)
    
    print("=" * 60)
    print(f"PASSED: {passed}/{total}  FAILED: {total-passed}/{total}")
    print(f"RESULT: {'PASS' if passed == total else 'FAIL'}")
    print("=" * 60)
    
    return results

# Execute for bench console
if __name__ == "__main__":
    RR = []
    try:
        RR = validate()
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
