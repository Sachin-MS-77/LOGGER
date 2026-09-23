"""Native Elasticsearch Bulk delivery. Item failures must never count as success."""
import json
import os
import re
from pathlib import Path
from .schema import ecs_export

def validate_index(value):
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,199}', value):
        raise ValueError('index must start with a lowercase letter/digit and use lowercase letters, digits, dot, underscore or hyphen')
    return value

async def send(client, row):
    if row.get('kind', 'http') == 'http':
        response = await client.post(row['url'], content=row['payload'], headers={
            'Content-Type':'application/json', 'Idempotency-Key':row['id']})
        response.raise_for_status()
        return
    index = validate_index(row.get('index_name') or 'logflux-events')
    event = json.loads(row['payload'])['event']
    document = ecs_export({'id':row['event_id'], 'normalized':event,
                          'received_at':event['time'], 'source':event.get('device',''),
                          'raw_hash':event.get('provenance',{}).get('raw_hash',''),
                          'status':'partial' if event.get('quality',{}).get('issues') else 'normalized'})
    document['logflux']['revision'] = row['revision']
    document['logflux']['delivery_id'] = row['id']
    # One immutable document per event revision. Retrying overwrites that same ID.
    body = json.dumps({'index':{'_index':index, '_id':f"{row['event_id']}:{row['revision']}"}})+'\n'+json.dumps(document)+'\n'
    headers = {'Content-Type':'application/x-ndjson'}
    token_file = os.getenv('LOGFLUX_ELASTIC_API_KEY_FILE')
    if token_file:
        if not row['url'].startswith('https://'):
            raise ValueError('authenticated Elasticsearch output requires HTTPS')
        headers['Authorization'] = 'ApiKey '+Path(token_file).read_text().strip()
    response = await client.post(row['url'].rstrip('/')+'/_bulk', content=body, headers=headers)
    response.raise_for_status()
    result = response.json()
    items = result.get('items', [])
    item = items[0].get('index', {}) if len(items)==1 else {}
    if result.get('errors') is not False or item.get('status') not in (200,201):
        # Server error bodies may contain raw data. Retain only the error type.
        raise ValueError('Elasticsearch item rejected: '+str(item.get('error',{}).get('type','invalid_bulk_response'))[:100])
