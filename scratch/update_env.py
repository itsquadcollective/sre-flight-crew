import os
env_path = '.env'
updates = {
    'AZURE_PROJECT_ENDPOINT': 'https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam',
    'AZURE_SUBSCRIPTION_ID': 'fbfa9c04-f426-4e29-b867-98b97012cdfc',
    'AZURE_RESOURCE_GROUP': 'rg-ochuko',
    'MODEL_DEPLOYMENT_NAME': 'gpt-4.1',
    'DIAGNOSER_AGENT_ID': 'none',
    'DIAGNOSER_AGENT_NAME': 'DIAGNOSER',
    'DIAGNOSER_AGENT_VERSION': '11'
}

lines = []
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

new_lines = []
keys_found = set()
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        k = k.strip()
        if k in updates and updates[k]:
            new_lines.append(f'{k}={updates[k]}\n')
            keys_found.add(k)
            continue
    new_lines.append(line)

for k, v in updates.items():
    if k not in keys_found and v:
        new_lines.append(f'{k}={v}\n')

with open(env_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Updated .env successfully.')
