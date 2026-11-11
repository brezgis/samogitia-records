import importlib.util
import unittest
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'pipeline'/f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


g = module('gazetteer')
r = module('reconcile')
h = module('htr_dataset')
ev = module('evaluate_htr')


class DataIntegrity(unittest.TestCase):
    def test_unreadable_is_not_agreement(self):
        a = {'scan': 93, 'entry_no': 3, 'village_ru': '[illegible]'}
        b = dict(a, village_ru='[not on this row]')
        stats, merged = r.compare([a], [b])
        self.assertEqual(stats['village_ru'], [0, 1])
        self.assertIn('village_ru', merged[0]['missing_both'])

    def test_duplicate_entries_raise(self):
        a = {'scan': 93, 'entry_no': 3}
        with self.assertRaises(ValueError):
            r.compare([a, a], [a])

    def test_identity_includes_scan(self):
        a = [{'scan': n, 'entry_no': 1} for n in [93, 94]]
        self.assertEqual(len(r.compare(a, a)[1]), 2)

    def test_uncertainty_is_preserved(self):
        a = {'scan': 93, 'entry_no': 3, 'village_ru': 'Варкали[?]', 'uncertain': ['village_ru']}
        stats, merged = r.compare([a], [a])
        self.assertEqual(merged[0]['village_ru'], 'Варкали[?]')
        self.assertIn('village_ru', merged[0]['flagged_by_reader'])
        self.assertEqual(merged[0]['status'], 'unreviewed')

    def test_empty_names_have_no_candidates(self):
        for v in [None, '', '[illegible]', '[not on this row]', '—', '[?]']:
            self.assertEqual(g.candidates(v, g.load_places()), [])

    def test_places_remain_proposals(self):
        p = g.proposal('Варкали[?]', g.load_places())
        self.assertEqual(p['candidates'][0]['name'], 'Varkaliai')
        self.assertIsNone(p['confirmed_place_id'])
        self.assertEqual(p['status'], 'candidate_only')
        self.assertEqual(p['original'], 'Варкали[?]')

    def test_modern_diacritics_and_historical_letters(self):
        self.assertEqual(g.key('Шатейки'), 'shateiki')
        self.assertEqual(g.key('Žemaičių'), 'zhemaichiu')
        self.assertEqual(g.key('Кліморы[?]'), g.key('Климоры'))

    def test_training_export_checks_source_pixels_and_skips_drafts(self):
        annotations=json.loads((ROOT/'data/plunge-1886-1890/training/annotations.json').read_text())
        checked=h.checked_labels(annotations)
        expected={a['id'] for a in annotations if a['status'] in ('image_checked','independently_checked')}
        self.assertGreaterEqual(len(checked),4)
        self.assertEqual({x['id'] for x in checked},expected)
        self.assertTrue(all(x['status'] in ('image_checked','independently_checked') for x in checked))

    def test_masked_crop_allows_only_fill_pixels(self):
        from PIL import Image
        src=Image.new('L',(4,1)); src.putdata([10,20,30,40])
        masked=Image.new('L',(4,1)); masked.putdata([10,200,30,40])
        self.assertTrue(h.crop_matches_source(masked,src,200))
        self.assertFalse(h.crop_matches_source(masked,src,None))
        self.assertFalse(h.crop_matches_source(masked,src,199))

    def test_training_rejects_uncertainty_hash_changes_and_split_leakage(self):
        annotation=h.checked_labels(json.loads((ROOT/'data/plunge-1886-1890/training/annotations.json').read_text()))[0]
        for field,value in [('text','Юзефъ[?]'),('image_sha256','changed'),('split','test')]:
            bad=copy.deepcopy(annotation);bad[field]=value
            with self.assertRaises(ValueError):h.checked_labels([bad])

    def test_target_year_and_layout_coverage(self):
        queue=json.loads((ROOT/'data/plunge-1886-1890/processed/queue.json').read_text())
        target=[r for r in queue if r['in_target_year']]
        self.assertEqual(len(target),434)
        self.assertEqual(len({r['row_id'] for r in queue}),len(queue))
        ids={r['row_id'] for r in target}
        self.assertNotIn('0092_R1',ids)
        self.assertNotIn('0125_R4',ids)
        self.assertNotIn('0144_L3',ids)
        self.assertTrue(all(r['scan']<145 for r in target))
        anchors={'0092_R2':1,'0093_L1':3,'0094_L1':10,'0111_L1':141,'0119_L1':221,
                 '0120_L1':231,'0121_L1':241,'0127_L1':297,'0143_L1':425,'0144_L2':434}
        self.assertEqual({r['row_id']:r['expected_entry_no'] for r in target if r['row_id'] in anchors},anchors)

    def test_cer_preserves_old_spelling_and_penalizes_missing_predictions(self):
        refs=[{'id':'a','text':'Юзефъ'},{'id':'b','text':'Анна'}]
        result=ev.evaluate(refs,[{'id':'a','text':'Юзеф'}])['all']
        self.assertEqual(result['character_errors'],5)
        self.assertEqual(result['characters'],9)
        self.assertEqual(result['missing_predictions'],1)
        self.assertEqual(result['exact_lines'],0)

    def test_evaluation_rejects_unknown_and_duplicate_predictions(self):
        refs=[{'id':'a','text':'Анна'}]
        with self.assertRaises(ValueError):ev.evaluate(refs,[{'id':'b','text':'Анна'}])
        with self.assertRaises(ValueError):ev.evaluate(refs,refs+refs)


if __name__ == '__main__':
    unittest.main()


class DraftAssembly(unittest.TestCase):
    def test_join_lines_rejoins_hyphenated_words(self):
        ad = module('assemble_drafts')
        self.assertEqual(ad.join_lines(['восьмаго года Апрѣля три-', 'надцатаго дня, въ Плун=', '=гянскомъ']),
                         'восьмаго года Апрѣля тринадцатаго дня, въ Плунгянскомъ')
        self.assertEqual(ad.join_lines(['Яна и Анны', '', 'изъ Сенковъ']), 'Яна и Анны изъ Сенковъ')

    def test_entry_start_detection_tolerates_misreads(self):
        ad = module('assemble_drafts')
        for s in ['Тысяча восемьсотъ', 'ысяча восемьсотъ восемьде-', 'Тиеяча восемьсотъ', 'нсяча восемьсотъ']:
            self.assertTrue(ad.is_entry_start(s), s)
        for s in ['сятъ восьмаго года', 'Крестьянъ Плунгянской', 'Францишекъ, со всѣми обрядами']:
            self.assertFalse(ad.is_entry_start(s), s)

    def test_column_start_detection(self):
        ad = module('assemble_drafts')
        self.assertTrue(ad.is_column_start('parents', 'Крестьянъ Плунгянской во-'))
        self.assertTrue(ad.is_column_start('parents', 'рестьянъ Плунгянской'))
        self.assertTrue(ad.is_column_start('godparents', 'Воспріемника-'))
        self.assertTrue(ad.is_column_start('godparents', 'оспріемниками были'))
        self.assertFalse(ad.is_column_start('parents', 'ныхъ Супруговъ сынъ'))
        self.assertFalse(ad.is_column_start('godparents', 'ми были Юзефъ'))


class YearInference(unittest.TestCase):
    def test_year_words_and_digits(self):
        iy = module('infer_years')
        self.assertEqual(iy.word_year('Тысяча восемьсотъ восемьдесятъ седьмаго года Мая'), 1887)
        self.assertEqual(iy.word_year('Тысяча восемьсотъ восемь десятъ шестаго года'), 1886)
        self.assertEqual(iy.word_year('Тысяча восемьсотъ восемьдесятъ девятаго года Января'), 1889)
        self.assertEqual(iy.word_year('Тысяча восемьсотъ девяностаго года Марта'), 1890)
        self.assertIsNone(iy.word_year('Января шестаго дня, въ Плунгянскомъ'))
        self.assertEqual(iy.digit_year('родившійся 1887 года Декабря'), 1887)
        self.assertEqual(iy.digit_year('родившаяся 18 89 года'), 1889)
        self.assertIsNone(iy.digit_year('Мая 12го дня'))

    def test_year_words_beyond_1890(self):
        iy = module('infer_years')
        self.assertEqual(iy.word_year('Тысяча восемьсотъ девяносто перваго года'), 1891)
        self.assertEqual(iy.word_year('Тысяча восемьсотъ девяносто пятаго года Мая'), 1895)
        self.assertEqual(iy.word_year('Тысяча девятисотаго года'), 1900)
        self.assertEqual(iy.word_year('Тысяча девятьсотъ третьяго года'), 1903)
        self.assertEqual(iy.word_year('Тысяча восемьсотъ семьдесятъ девятаго года'), 1879)
        self.assertEqual(iy.digit_year('родившійся 1893 года'), 1893)
