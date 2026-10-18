import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent.services import seko_local_workflow as w

JOB='eedacf2c-49c2-4b6f-9f02-652d60834930'

class ResidentLookupTest(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=patch.object(w,'ROOT',Path(temp.name));root.start();self.addCleanup(root.stop)
        w.job_dir(JOB).mkdir(parents=True)
        self.state={'jobId':JOB,'canvasId':'100','storyId':'200',
            'assembly':{'target':{'canvasId':'300'},'timeline':{'storyId':'400'}},
            'multishot':{'canvasId':'500','timeline':{'storyId':'600'}}}
        (w.job_dir(JOB)/'state.json').write_text(json.dumps(self.state))

    def test_source_and_both_exports_resolve_the_same_local_task(self):
        for key in ['100','200','300','400','500','600']:
            with self.subTest(key=key):self.assertEqual(w.list_jobs(key),[self.state])

    def test_unrelated_partial_and_empty_ids_do_not_leak_jobs(self):
        for key in ['10','1000','999','',None]:
            with self.subTest(key=key):self.assertEqual(w.list_jobs(key),[])

    def test_uncreated_later_steps_do_not_create_phantom_ownership(self):
        self.state.pop('assembly');self.state.pop('multishot')
        (w.job_dir(JOB)/'state.json').write_text(json.dumps(self.state))
        self.assertEqual(w.list_jobs('100'),[self.state]);self.assertEqual(w.list_jobs('600'),[])

if __name__=='__main__':unittest.main()
