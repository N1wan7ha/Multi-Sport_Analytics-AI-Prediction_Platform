from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from ml_engine.loader import rank_versions, save_bundle, select_best_version
from ml_engine.vector_db_integration import compute_team1_bias_from_contexts


class ModelVersionRankingTests(SimpleTestCase):
    def test_select_best_version_prefers_higher_composite_score(self):
        with TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)

            save_bundle(
                str(model_path),
                'v1.0',
                {'type': 'sklearn_ensemble'},
                {
                    'sample_count': 100,
                    'model_type': 'sklearn_ensemble',
                    'accuracy': 0.65,
                    'auc_roc': 0.68,
                    'brier_score': 0.28,
                },
            )
            save_bundle(
                str(model_path),
                'v2.0',
                {'type': 'sklearn_ensemble'},
                {
                    'sample_count': 2000,
                    'model_type': 'sklearn_ensemble',
                    'accuracy': 0.82,
                    'auc_roc': 0.9,
                    'brier_score': 0.14,
                },
            )

            selected = select_best_version(str(model_path))
            self.assertEqual(selected, 'v2.0')

    def test_rank_versions_returns_score_breakdown(self):
        with TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)

            save_bundle(
                str(model_path),
                'v1.0',
                {'type': 'fallback'},
                {
                    'sample_count': 50,
                    'model_type': 'fallback',
                    'accuracy': 0.55,
                    'auc_roc': 0.57,
                    'brier_score': 0.31,
                },
            )

            ranked = rank_versions(str(model_path))
            self.assertEqual(len(ranked), 1)
            self.assertEqual(ranked[0]['version'], 'v1.0')
            self.assertIn('components', ranked[0])
            self.assertIn('accuracy_component', ranked[0]['components'])
            self.assertIn('auc_component', ranked[0]['components'])
            self.assertIn('brier_component', ranked[0]['components'])


class VectorContextBiasTests(SimpleTestCase):
    def test_compute_team1_bias_from_contexts_weighted(self):
        contexts = [
            {
                'winner_team': 'India',
                '_additional': {'certainty': 0.9},
            },
            {
                'winner_team': 'India',
                '_additional': {'certainty': 0.7},
            },
            {
                'winner_team': 'England',
                '_additional': {'certainty': 0.4},
            },
        ]

        bias, count = compute_team1_bias_from_contexts(contexts, team1_name='India', team2_name='England')
        self.assertEqual(count, 3)
        self.assertGreater(bias, 0.0)
        self.assertLessEqual(bias, 1.0)

    def test_compute_team1_bias_returns_zero_for_empty(self):
        bias, count = compute_team1_bias_from_contexts([], team1_name='India', team2_name='England')
        self.assertEqual(count, 0)
        self.assertEqual(bias, 0.0)
