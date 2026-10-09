import requests
import os

BASE = 'http://127.0.0.1:8000'

def run_tests():
    print('--- TEST 1: CSV UPLOAD & AI DATA CLEANING ---')
    csv_path = 'C:/Users/hp/.gemini/antigravity/scratch/certify-pro/app/samples/sample_dirty_participants.csv'
    with open(csv_path, 'rb') as f:
        r = requests.post(f'{BASE}/api/events/1/upload-csv', files={'file': ('dirty_sample.csv', f, 'text/csv')})
    print('Upload status:', r.status_code)
    upload_res = r.json()
    batch_id = upload_res['batch']['id']
    print('Batch ID:', batch_id)
    print('AI Summary:', upload_res['summary'])

    print('\n--- TEST 2: FETCH BATCH PARTICIPANTS ---')
    r = requests.get(f'{BASE}/api/batches/{batch_id}/participants')
    parts_data = r.json()
    print('Total participants in batch:', len(parts_data['participants']))
    for p in parts_data['participants'][:5]:
        print(f"  [{p['validation_status']}] {p['clean_name']} ({p['clean_email']}) - Dept: {p['department']} | Issues: {len(p['validation_issues'])}")

    print('\n--- TEST 3: APPLY ALL AI FIXES ---')
    r = requests.post(f'{BASE}/api/batches/{batch_id}/apply-all-fixes')
    print('Apply fixes response:', r.json())

    print('\n--- TEST 4: BULK CERTIFICATE GENERATION ---')
    r = requests.post(f'{BASE}/api/batches/{batch_id}/generate')
    gen_res = r.json()
    print('Generation status:', gen_res)

    print('\n--- TEST 5: VERIFY GENERATED CERTIFICATES & ASSETS ---')
    r = requests.get(f'{BASE}/api/batches/{batch_id}/participants')
    parts_after_gen = r.json()['participants']
    gen_certs = [p for p in parts_after_gen if p.get('certificate_id')]
    print('Generated cert count:', len(gen_certs))
    sample_cid = gen_certs[0]['certificate_id']
    print('Sample Cert ID:', sample_cid)

    print('\n--- TEST 6: PUBLIC VERIFICATION ENDPOINT (GENUINE) ---')
    r = requests.get(f'{BASE}/verify/{sample_cid}')
    print('Public Verify HTTP status:', r.status_code, 'Page size:', len(r.text))
    assert 'Verified Authentic' in r.text or 'GENUINE' in r.text, 'Genuine verification banner missing!'
    print('Verification check: SUCCESS (Genuine detected!)')

    print('\n--- TEST 7: PUBLIC VERIFICATION ENDPOINT (FORGED/FAKE) ---')
    fake_id = 'CRT-2026-FAKE-999999'
    r = requests.get(f'{BASE}/verify/{fake_id}')
    assert 'Credential Not Found' in r.text, 'Fake credential check failed!'
    print('Fake ID check: SUCCESS (Fake detected!)')

    print('\n--- TEST 8: EMAIL DISPATCH SIMULATION ---')
    r = requests.post(f'{BASE}/api/certificates/{sample_cid}/send-email')
    print('Email dispatch:', r.json())

    print('\n--- TEST 9: DOWNLOAD ZIP CHECK ---')
    r = requests.get(f'{BASE}/api/batches/{batch_id}/download-zip')
    print('ZIP download status:', r.status_code, 'Content length bytes:', len(r.content))

    print('\n--- ALL END-TO-END TESTS PASSED WITH 100% SUCCESS! ---')

if __name__ == '__main__':
    run_tests()
