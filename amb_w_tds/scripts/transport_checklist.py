"""
Transport Checklist Script for PH12.6
Generates pre-transport validation report for amb_w_tds and raven_ai_agent

Usage:
    bench execute amb_w_tds.scripts.transport_checklist.execute
"""
import frappe
import subprocess
import os


def execute():
    print("=" * 60)
    print("PH12.6 Transport Checklist")
    print("=" * 60)
    
    results = {}
    
    # 1. Current branch and commit for amb_w_tds
    print("\n[1] amb_w_tds Repository Status")
    print("-" * 40)
    amb_status = get_git_status("/workspace/amb_w_tds")
    print(amb_status)
    results["amb_w_tds"] = amb_status
    
    # 2. Current branch and commit for raven_ai_agent (if exists)
    print("\n[2] raven_ai_agent Repository Status")
    print("-" * 40)
    raven_path = "/workspace/raven_ai_agent"
    if os.path.exists(raven_path):
        raven_status = get_git_status(raven_path)
        print(raven_status)
        results["raven_ai_agent"] = raven_status
    else:
        print("raven_ai_agent not found in workspace")
        results["raven_ai_agent"] = "NOT FOUND"
    
    # 3. List modified files since V12.4.0
    print("\n[3] Modified Files Since V12.4.0")
    print("-" * 40)
    modified = get_modified_files("/workspace/amb_w_tds")
    for f in modified:
        print(f"  {f}")
    results["modified_files"] = modified
    
    # 4. DocType validation
    print("\n[4] DocType Pre-transport Validation")
    print("-" * 40)
    doctype_issues = validate_doctypes("/workspace/amb_w_tds")
    if doctype_issues:
        print("ISSUES FOUND:")
        for issue in doctype_issues:
            print(f"  - {issue}")
    else:
        print("All DocTypes OK: custom=1 and module=amb_w_tds")
    results["doctype_issues"] = doctype_issues
    
    print("\n" + "=" * 60)
    print("Transport Checklist Complete")
    print("=" * 60)
    
    return results


def get_git_status(repo_path):
    """Get git branch and commit hash"""
    try:
        # Get branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        branch = branch_result.stdout.strip()
        
        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        commit_hash = hash_result.stdout.strip()[:8]
        
        return f"Branch: {branch}, Commit: {commit_hash}"
    except Exception as e:
        return f"Error: {str(e)}"


def get_modified_files(repo_path):
    """Get list of modified files since V12.4.0"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "V12.4.0..HEAD", "--name-only", "--pretty=format:"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        # Remove duplicates
        return list(set(files))
    except Exception as e:
        return [f"Error: {str(e)}"]


def validate_doctypes(repo_path):
    """Validate DocType JSONs have custom=1 and module=amb_w_tds"""
    import json
    issues = []
    
    doctype_paths = [
        f"{repo_path}/amb_w_tds/doctype/batch_amb/batch_amb.json",
    ]
    
    # Also check subdirectories
    import glob
    for json_file in glob.glob(f"{repo_path}/amb_w_tds/doctype/**/*.json", recursive=True):
        if "batch_amb" in json_file.lower():
            doctype_paths.append(json_file)
    
    for json_file in doctype_paths:
        if not os.path.exists(json_file):
            continue
            
        try:
            with open(json_file, "r") as f:
                doc = json.load(f)
            
            # Check custom field
            if not doc.get("custom"):
                issues.append(f"{os.path.basename(json_file)}: missing custom=1")
            
            # Check module field
            if doc.get("module") != "amb_w_tds":
                issues.append(f"{os.path.basename(json_file)}: module should be amb_w_tds")
        except Exception as e:
            issues.append(f"{os.path.basename(json_file)}: {str(e)}")
    
    return issues
