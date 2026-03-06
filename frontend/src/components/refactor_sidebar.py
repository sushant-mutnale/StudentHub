import os
import re

files_to_modify = [
    'Profile.jsx',
    'StudentDashboard.jsx',
    'SmartNotifications.jsx',
    'SkillGapAnalysis.jsx',
    'RecruiterDashboard.jsx',
    'ResumeUpload.jsx',
    'Opportunities.jsx',
    'Notifications.jsx',
    'MockInterview.jsx',
    'LearningPath.jsx',
    'CompanyResearch.jsx',
    'Assessment.jsx',
    'ApplicationTracker.jsx',
    'ApplicationPipeline.jsx',
    'interviews/InterviewsPage.jsx',
    'Analytics/AnalyticsDashboard.jsx'
]

base_dir = r'd:\python\project\StudentHub\frontend\src\components'

def process_file(content):
    # 1. Remove import
    content = re.sub(r"import\s+SidebarLeft\s+from\s+['\"].*?SidebarLeft['\"];?\s*\n", "", content)
    # 2. Remove SidebarLeft usage
    content = re.sub(r"<\s*SidebarLeft\s*/?>", "", content)
    
    # 3. Find dashboard-container
    match = re.search(r"<div\s+className=[\"']dashboard-container[\"'][^>]*>", content)
    if not match:
        return content
    
    start_idx = match.start()
    end_idx = match.end()
    
    counter = 1
    pos = end_idx
    
    while counter > 0 and pos < len(content):
        next_open = content.find("<div", pos)
        next_close = content.find("</div", pos)
        
        if next_open == -1: next_open = float('inf')
        if next_close == -1: next_close = float('inf')
        
        if next_open == float('inf') and next_close == float('inf'):
            break
            
        if next_open < next_close:
            counter += 1
            pos = next_open + 4
        else:
            counter -= 1
            if counter == 0:
                part1 = content[:start_idx] + "<>"
                part2 = content[end_idx:next_close]
                part3 = "</>" + content[next_close+6:]
                return part1 + part2 + part3
            pos = next_close + 5
                
    return content

for f in files_to_modify:
    path = os.path.join(base_dir, f)
    if not os.path.exists(path):
        print(f"Skipping {f}, not found.")
        continue
        
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
        
    new_content = process_file(content)
    
    with open(path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    print(f'Processed {f}')
