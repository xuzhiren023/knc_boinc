"""Keep compact, unmodified result fields before regenerating large kernels."""
import json
from pathlib import Path
import sys
root=Path('twin/multicore')
fields=('status','message','scale','python_execution_seconds','functional_check',
        'result_class','assumptions','unsupported','limiting_constraints','calibration_status')
runs={}
for name in ('baseline','unit','ring','compare-unit','compare-ring'):
    result=json.loads((root/('chunk-'+name)/'result.json').read_text())
    row={key:result.get(key) for key in fields}
    params=result.get('parameters_used',{})
    row['parameters_used']={key:value for key,value in params.items()
                            if isinstance(value,dict) and value.get('status') in ('assumed','derived')}
    row['argv']=result['invocation']['argv']
    row['profile_hash']=(result.get('profile') or {}).get('hash')
    row['unit_of_work']=result.get('input',{}).get('kernel',{}).get('unit_of_work')
    # No prediction data is extracted from failed envelopes.
    if result['status']=='ok':
        row['prediction']=result.get('prediction')
    runs[name]=row
evidence={'requested_bodies_per_context':128,
    'bodies_per_context_configured':runs['baseline']['unit_of_work']['count']//4,
    'requested_experiment_complete':False,
    'blocker':'knc-twin 0.4.0 x87 double rounding fails native PC53 arithmetic; no valid 1-to-8-core ratio',
    'build':json.loads((root/'chunk-build-evidence.json').read_text()), 'runs':runs}
(root/sys.argv[1]).write_text(json.dumps(evidence,indent=2)+'\n')
print('Saved '+sys.argv[1]+': '+', '.join(name+'='+row['status'] for name,row in runs.items()))
