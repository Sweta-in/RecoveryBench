import json, sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\Sweta Jha\.gemini\antigravity-ide\brain\a5da185a-11de-4222-9d5e-af636c8d477c\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('step_index') == 0:
            content = obj.get('content', '')
            # Print from start of checkpoint section
            # The content before position 3129 should have the start of CP2
            # Let's find "CHECKPOINT 2" properly
            upper = content.upper()
            idx = upper.find('CHECKPOINT 2')
            # First occurrence might be in checkpoint 1's "next action" 
            # Let's find all occurrences
            pos = 0
            occurrences = []
            while True:
                idx = upper.find('CHECKPOINT 2', pos)
                if idx == -1:
                    break
                occurrences.append(idx)
                pos = idx + 1
            print(f'Found {len(occurrences)} occurrences at: {occurrences}')
            
            # The first one that starts a section should be the heading
            for occ in occurrences:
                # Check if this looks like a heading
                line_start = content.rfind('\n', max(0, occ-100), occ)
                context = content[max(0, line_start):occ+50]
                if '##' in context or '---' in context:
                    print(f'\nCheckpoint 2 heading near position {occ}:')
                    print(content[max(0,occ-200):occ+4000])
                    break
            break
