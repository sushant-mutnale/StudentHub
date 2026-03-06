import os
import re

files_to_fix = [
    'SmartNotifications.jsx',
    'SkillGapAnalysis.jsx',
    'ResumeUpload.jsx',
    'Profile.jsx',
    'MockInterview.jsx',
    'Opportunities.jsx',
    'LearningPath.jsx',
    'JobDetail.jsx',
    'CompanyResearch.jsx',
    'ApplicationTracker.jsx',
    'Analytics/AnalyticsDashboard.jsx'
]

base_dir = r'd:\\python\\project\\StudentHub\\frontend\\src\\components'

for f in files_to_fix:
    path = os.path.join(base_dir, f)
    if not os.path.exists(path):
        print(f"File not found: {f}")
        continue
        
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'className="dashboard-container"' not in content:
        print(f"Skipping {f}, no dashboard-container found.")
        continue
        
    # 1. Replace the exact opening tag
    content = re.sub(r'<div\s+className=["\']dashboard-container["\'](?:\s+style=\{\{[^}]*\}\})?\s*>', '<>', content, count=1)
    
    # 2. Replace the matching closing tag. It's the last closing div before the end of the return statement.
    parts = content.rsplit(');', 1)
    if len(parts) == 2:
        last_chunk = parts[0]
        last_div_idx = last_chunk.rfind('</div')
        if last_div_idx != -1:
            close_bracket_idx = last_chunk.find('>', last_div_idx)
            if close_bracket_idx != -1:
                parts[0] = last_chunk[:last_div_idx] + '</>' + last_chunk[close_bracket_idx+1:]
        content = ');'.join(parts)
        
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)
        
    print(f"Fixed {f}")
