# Test Script: Run Scanner Skill Directly
# Run this inside the Docker container to find the exact error

# Step 1: SSH into your production server
ssh root@72.62.131.198

# Step 2: Enter the container
docker exec -it erpnext-backend-1 bash

# Step 3: Go to bench and enter console
cd /home/frappe/frappe-bench
bench console

# Step 4: Run this exact test code:
from raven_ai_agent.skills.data_quality_scanner.skill import DataQualityScannerSkill
scanner = DataQualityScannerSkill()
result = scanner.handle("scan SO-00767-BARENTZ Italia", {})
print("RESULT:", result)

# If there's an error, it will show here
