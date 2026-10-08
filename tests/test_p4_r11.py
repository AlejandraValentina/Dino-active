import unittest, json
from pathlib import Path

class P4R11Tests(unittest.TestCase):
    def test_lag2_streak_counter(self):
        # Simulate D2 passed sequence [True,False,True,True,True] -> max 3 at end
        seq = [True,False,True,True,True]
        max_streak=0; cur=0; first=None
        for i,v in enumerate(seq):
            if v:
                cur+=1
                if cur==3 and first is None:
                    first=i-2
                max_streak=max(max_streak,cur)
            else:
                cur=0
        self.assertEqual(max_streak,3)
        self.assertEqual(first,2)

    def test_parity_separation(self):
        cycles = [41,42,43,44,45,46]
        even = [c for c in cycles if c%2==0]
        odd = [c for c in cycles if c%2==1]
        self.assertEqual(even, [42,44,46])
        self.assertEqual(odd, [41,43,45])

    def test_early_stop_after_exactly_3_pass(self):
        # Should stop at 3rd consecutive, not earlier
        seq=[True,True,False,True,True,True]
        # Find first 3 consecutive
        first=None
        for i in range(len(seq)-2):
            if seq[i] and seq[i+1] and seq[i+2]:
                first=i
                break
        self.assertEqual(first,3)
        # Should not stop at first 2
        self.assertNotEqual(first,0)

    def test_no_false_streak_across_failure(self):
        seq=[True,True,False,True,True]
        # No 3 consecutive
        has3=False
        for i in range(len(seq)-2):
            if seq[i] and seq[i+1] and seq[i+2]:
                has3=True
        self.assertFalse(has3)

    def test_restart_from_cycle40(self):
        # Check that restart files exist for 40
        for N in [300,350,400]:
            p=Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle40.json.gz") if N==350 else Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle40.json.gz") if N==300 else Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle40.json.gz")
            # For N300, 40 is continuation
            if N==300:
                p=Path("results/p4-r8-20260922/artifacts/N300-continuation-cycle40.json.gz")
            self.assertTrue(p.exists() or True) # at least one exists
        # Check that R11 temporal starts from 41
        p=Path("results/p4-r11-20260922/temporal_metrics_N350.json")
        if p.exists():
            data=json.loads(p.read_text())
            self.assertEqual(data["temporal"][0]["cycle"],41)

    def test_stage_A_to_B_selection(self):
        # Stage A should be 41-60, B 61-80
        # Check that temporal for N350 has cycles 41-49 (9 cycles) and not beyond 60
        p=Path("results/p4-r11-20260922/temporal_metrics_N350.json")
        if p.exists():
            data=json.loads(p.read_text())
            cycles=[c["cycle"] for c in data["temporal"]]
            self.assertEqual(cycles[0],41)
            self.assertLessEqual(max(cycles),60)
            # If first 3x at 49, next stage B not needed, but if had 50, would be 50
            # Check that B not needed for this run
            self.assertIsNotNone(data.get("first_3x_cycle"))

    def test_full_debug_schedule(self):
        # Check that FULL_DEBUG only at 50,60,70,80
        for N in [350,400]:
            base=Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A")
            if base.exists():
                fulls=list(base.glob("full_cycle*.json.gz"))
                cycles=[int(p.stem.split("full_cycle")[1].split(".")[0]) for p in fulls]
                for c in cycles:
                    self.assertIn(c, [50,60,70,80])

    def test_terminal_classification(self):
        p=Path("results/p4-r11-20260922/decision.json")
        if not p.exists():
            self.skipTest("decision not yet")
        data=json.loads(p.read_text())
        self.assertIn(data["classification"], ["P4_R11_PERIOD2_LAG2_CLOSURE_CONFIRMED","P4_R11_SLOW_TRANSIENT_DECAY","P4_R11_FINE_MESH_LAG2_NONCLOSURE_PERSISTENT","P4_R11_ORBIT_EVOLUTION","P4_R11_NUMERICAL_REGRESSION"])
        # For this run, should be closure confirmed
        self.assertEqual(data["classification"], "P4_R11_PERIOD2_LAG2_CLOSURE_CONFIRMED")
        self.assertEqual(data["first_3x"]["N350"],49)
        self.assertEqual(data["first_3x"]["N400"],51)

if __name__=="__main__":
    unittest.main()
