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
        for t in ['Крентьянъ Іосифа и Марты', 'Крестинъ Іеррія и Ка', 'Тельшевскаго Мѣщанина Ферды']:
            self.assertTrue(ad.is_column_start('parents', t), t)
        for t in ['19 Тысяча восемсотъ шестьдесятъ', 'Тысоча восемсотъ', 'Тысча Косемсотъ']:
            self.assertTrue(ad.is_entry_start(t), t)
        for t in ['Таинства. -', 'тоже.', 'дня въ деревни']:
            self.assertFalse(ad.is_entry_start(t), t)

    def test_month_heading_is_recognised_conservatively(self):
        ad = module('assemble_drafts')
        self.assertEqual([ad.heading_month(t) for t in ['Ноябрь.', 'оябрь', 'Авгусmъ', 'Май', 'тоже.', 'Мѣсяцъ']],
                         [11, 11, 8, 5, 0, 0])
        for t in ['Ноября', 'Мая', 'Іюля', 'Прихода. -', 'Супругою. -', 'года Ноябрь', '']:
            self.assertIsNone(ad.heading_month(t), t)

    def test_previous_entry_tail_and_heading_leave_the_next_entry(self):
        """Layout puts the row boundary a line too high: the first entry's last line and a month
        heading lie inside the second row, and the line boxes overlap."""
        ad = module('assemble_drafts')
        def line(n, row, cell, top, bottom, core, text):
            x = {'baptism': 100, 'parents': 600, 'godparents': 1100}[cell]
            return ({'id': f'{row}_{cell}_{n:02}', 'row_id': row, 'cell': cell, 'bbox': [x, top, x + 400, bottom],
                     'line': {'x': x + 200, 'slope': -0.03, 'band': [top, bottom], 'core': [core, core + 18]}}, text)
        made = [line(1, 'A', 'baptism', 100, 220, 150, 'Тысяча восемсотъ'), line(2, 'A', 'baptism', 190, 300, 240, 'окрещенъ Янъ'),
                line(1, 'A', 'parents', 100, 220, 150, 'Крестьянъ Яна и'), line(1, 'A', 'godparents', 100, 220, 150, 'Воспріемниками были'),
                # filed under row B by the layout (B starts at y=390):
                line(1, 'B', 'baptism', 380, 520, 440, 'Со всѣми обрядами Таинства. -'),
                line(2, 'B', 'baptism', 450, 600, 540, 'Тысяча восемсотъ'), line(3, 'B', 'baptism', 570, 700, 630, 'шестьдесятъ перваго'),
                line(1, 'B', 'parents', 380, 470, 420, 'Прихода. -'), line(2, 'B', 'parents', 430, 530, 480, 'Ноябрь.'),
                line(3, 'B', 'parents', 500, 620, 560, 'Крестьянъ Іосифа и'),
                line(1, 'B', 'godparents', 400, 500, 450, 'тоже.'), line(2, 'B', 'godparents', 480, 600, 550, 'Воспріемниками были:')]
        props, text_of = [p for p, _ in made], {p['id']: t for p, t in made}
        queue = [{'row_id': 'A', 'scan': 1, 'page': 'L', 'focal_y': [100, 390]}, {'row_id': 'B', 'scan': 1, 'page': 'L', 'focal_y': [390, 800]}]
        by_row, _ = ad.reassign(queue, props, text_of)
        texts = {r: [text_of[p['id']] for p in ls] for r, ls in by_row.items()}
        self.assertEqual(texts['A'], ['Тысяча восемсотъ', 'окрещенъ Янъ', 'Со всѣми обрядами Таинства. -', 'Крестьянъ Яна и',
                                      'Прихода. -', 'Воспріемниками были'])
        self.assertEqual(texts['B'], ['Тысяча восемсотъ', 'шестьдесятъ перваго', 'Крестьянъ Іосифа и', 'Воспріемниками были:'])
        self.assertEqual({c: [text_of[p['id']] for p in ps] for c, ps in ad.reassign.headings['B'].items()},
                         {'parents': ['Ноябрь.'], 'godparents': ['тоже.']})

    def test_printed_heading_is_matched_on_its_own_words(self):
        ad = module('assemble_drafts')
        head = {'baptism': 'кога, цзъ, сто икемъ, одною ли содою, ияъ со всѣмъ обрязами таинства окрещенъ -',
                'parents': 'какихъ родичелей, хогда и 1зъг.с., въ каконъ приходъ родияся крещенный.',
                'godparents': 'воспріемники при Съ. Крещеній и тго присучствоватъ.'}
        self.assertEqual(ad.printed_heading_columns(head), 3)
        # the tail of the baptism heading is also the tail of every entry: a continuation row is no heading
        tail = {'baptism': 'Монкевичемъ окрещенъ младенецъ именемъ Барбара совсѣми обрядами таинства.',
                'parents': 'Салантовскаго Прихода въ деревнѣ Имбарехъ', 'godparents': '-'}
        self.assertEqual(ad.printed_heading_columns(tail), 0)
        entry = {'baptism': 'Тысяча восемсотъ пятьдесятъ девятаго года Апрѣля двадцатаго дня въ Салантовскомъ',
                 'parents': 'Крестьянъ Феликса и Саломеи урожденной Луновичевной Марковскихъ Законныхъ Супруговъ Сынъ родившійся',
                 'godparents': 'Воспріемниками были Крестьянъ Антоній Валоюсъ съ Антониною Петрыковною дивицею.'}
        self.assertEqual(ad.printed_heading_columns(entry), 0)

    def test_clipped_first_word_is_still_an_entry_opening(self):
        ad = module('assemble_drafts')
        for t in ['сяча восемьсотъ девяносто восьмаго года Февраля девятаго дня', 'восемьсотъ давяносто восьмаго года Марта',
                  'Трысясо Восемсотъ коть дсся семаго Года']:
            self.assertTrue(ad.opens_with_year(t), t)
        for t in ['Монкевичемъ окрещенъ младенецъ именемъ Барбара совсѣми обрядами таинства.', 'миръ со всеми обрядами Таинства', '']:
            self.assertFalse(ad.opens_with_year(t), t)

    def test_heading_row_is_dropped_and_fragment_folded_without_entry_numbers(self):
        """A page side of a book without side-column numbers: the printed heading row, an entry, the
        lower half of that entry cut off by the layout, an entry, and a row that has lost its
        baptism opening but opens its other columns (kept, not folded)."""
        ad = module('assemble_drafts')
        made, queue = [], []
        def row(rid, top, bottom, **cols):
            queue.append({'row_id': rid, 'scan': 1, 'page': 'L', 'focal_y': [top, bottom]})
            for cell, texts in cols.items():
                x = {'baptism': 100, 'parents': 600, 'godparents': 1100}[cell]
                for n, t in enumerate(texts):
                    y = top + 10 + 60 * n
                    made.append(({'id': f'{rid}_{cell}_{n + 1:02}', 'row_id': rid, 'cell': cell, 'bbox': [x, y, x + 400, y + 50]}, t))
        row('H', 160, 480, baptism=['когда, гзъ, кто икенъ, одною ли возою, пли', 'со всѣми обрядами таинства окрещенъ -'],
            parents=['какихъ родителей, когда и гдъ, г.с.,', 'въ каконъ приходъ родился крещенный.'],
            godparents=['кто были по имени и прозванію', 'воспріемники при Съ Крещеніи', 'и кто присутствовалъ.'])
        row('A', 480, 900, baptism=['Тысяча восемсотъ пятьдесятъ', 'девятаго года Марта', 'Костелѣ Викарнымъ Ксендзомъ Петромъ Сташ-'],
            parents=['Крестьянъ Іосифа и Анны урожденной', 'лашіовны Пацюсовъ Законныхъ Су-'],
            godparents=['Воспріемниками были Крестьянъ', 'Іосифъ Тваріонасъ съ Людо-'])
        row('A2', 900, 1200, baptism=['ковскимъ окрещено дитя именемъ Казимиръ'], parents=['пруговъ Сынъ родившійся 1859 года'],
            godparents=['викою Михаила Петкуса Супругою. -'])
        row('B', 1200, 1700, baptism=['Тысяча восемсотъ пятьдесятъ', 'девятаго года Апрѣля'], parents=['Крестьянъ Яна и Барбары'],
            godparents=['Воспріемниками были Крестьянъ Янъ'])
        row('C', 1700, 2200, baptism=['миръ со всеми обрядами Таинства'], parents=['Крестьянъ Яна и Виктори урожденной'],
            godparents=['Воспріемниками были Крестьяне'])
        props, text_of = [p for p, _ in made], {p['id']: t for p, t in made}
        by_row, _, _ = ad.reassign(queue, props, text_of, split_missed=True, text_fold=True)
        self.assertEqual(ad.reassign.heading_rows, ['H'])
        self.assertEqual(ad.reassign.folded, ['A2'])
        self.assertEqual(sorted(by_row), ['A', 'B', 'C'])
        texts = {r: [text_of[p['id']] for p in ls] for r, ls in by_row.items()}
        self.assertEqual(texts['A'][:4], ['Тысяча восемсотъ пятьдесятъ', 'девятаго года Марта', 'Костелѣ Викарнымъ Ксендзомъ Петромъ Сташ-',
                                          'ковскимъ окрещено дитя именемъ Казимиръ'])
        self.assertEqual(texts['A'][-1], 'викою Михаила Петкуса Супругою. -')
        self.assertFalse(any('родителей' in t or 'присутств' in t for ts in texts.values() for t in ts))
        # with entry numbers the text rule is not used; without the option nothing is folded
        ad.reassign(queue, props, text_of, split_missed=True)
        self.assertEqual(ad.reassign.folded, [])


class OlderWording(unittest.TestCase):
    """1849-1874 formula: no township, "урожденной", day in digits, "Ксендзомъ"."""

    def test_parents_between_estate_and_urozhdennoy(self):
        pe = module('parse_entries')
        f = pe.parse({'baptism': 'Тысяча Восемсотъ Патьдесятъ Семого года Марта однадцатаго дня въ Салантов скомъ Приходскомъ '
                                 'Римско-Китолическомъ Костелѣ, мѣстнымъ Викарнымъ Кондзомъ Коспромъ Янушевичемъ окрещенъ младенецъ '
                                 'Именемъ Іозефъ со всѣми обрядами Таинства-',
                      'parents': 'Крестьянъ Іозефа и Барбары урожденной Забытисовны Микаловскихъ законныхъ Супруговъ сынъ родившійся '
                                 'сего Года Марта десятого дня всчеромъ. Салантовскаго Прихода въ Деревни Тузаръ. -',
                      'godparents': 'Воспріемниками были Крестьянаянъ Якмесъ съ Катартыною Стунговною дѣвицею. -', 'register_year': 1857})
        self.assertEqual((f['father'], f['mother'], f['maiden_and_surname']), ('Іозефа', 'Барбары', 'Забытисовны Микаловскихъ'))
        self.assertEqual((f['baptism_date'], f['birth_date'], f['village'], f['sex']), ('1857-03-11', '1857-03-10', 'Тузаръ', 'M'))
        self.assertEqual(f['priest'], 'Коспромъ Янушевичемъ')
        self.assertIsNone(f['township'])

    def test_noisy_anchors_split_words_and_other_estates(self):
        pe = module('parse_entries')
        p = lambda t: pe.parse({'baptism': '', 'parents': t, 'godparents': ''})
        f = p('Крестьянъ Стани Слава и Марціян ны урожденной Вайтковной Фе балювъ Закон ныхъ супруговъ Дочь родившаяся 1851. года')
        self.assertEqual((f['father'], f['mother'], f['maiden_and_surname']), ('СтаниСлава', 'Марціянны', 'Вайтковной Фе балювъ'))
        f = p('Давинстняго Сондата Францишка и Анны уро денной Ветошевной Нарвиліовъ Законныхъ Супру')
        self.assertEqual((f['father'], f['mother'], f['maiden_and_surname']), ('Францишка', 'Анны', 'Ветошевной Нарвиліовъ'))
        # "законныхъ" unreadable: up to "супруговъ", less the word before it
        f = p('Крестьянъ Антона и Анны урожденной Іосковдзевной Дронсутовъ Занттовичъ Супруговъ Сынъ 19 Сентября родиля въ')
        self.assertEqual((f['father'], f['maiden_and_surname']), ('Антона', 'Іосковдзевной Дронсутовъ'))
        self.assertEqual((f['birth_month'], f['birth_day']), (9, 19))
        # abbreviated, after a township (1902-07)
        f = p('Крестьянъ Плунгянской волости Іосифа и Анны урожд. Стонкусъ зак. суп. сынъ родившійся')
        self.assertEqual((f['father'], f['mother'], f['maiden_and_surname']), ('Іосифа', 'Анны', 'Стонкусъ'))

    def test_unmarried_mother_gives_no_father(self):
        pe = module('parse_entries')
        for t in ['Крестьянки Анны Вашиковной незаконнорожденный сынъ 1. Мая въ деревни Кулъ',
                  'Крестьянки Марья ны Виршило вной нечаконно рожденнвй сыенъ Февраля вѣчеромъ Плунгянскаго Прихода']:
            f = pe.parse({'baptism': '', 'parents': t, 'godparents': ''})
            self.assertIsNone(f.get('father'), t)
            self.assertIsNone(f.get('maiden_and_surname'), t)

    def test_later_wording_is_untouched(self):
        pe = module('parse_entries')
        f = pe.parse({'baptism': '', 'godparents': '', 'parents': 'Крестьянъ Плунгянской волости Антона и Барбары изъ Валтіовъ '
                      'Августиновъ законныхъ супруговъ сынъ родившійся 1887 года Іюня 27 дня въ деревни Лонкелавки сего прихода. -'})
        self.assertEqual((f['township'], f['father'], f['mother'], f['maiden_and_surname'], f['village']),
                         ('Плунгянской', 'Антона', 'Барбары', 'Валтіовъ Августиновъ', 'Лонкелавки'))

    def test_baptism_day_in_digits_and_priest_without_rank(self):
        pe = module('parse_entries')
        b = lambda t: pe.parse({'baptism': t, 'parents': '', 'godparents': '', 'register_year': 1858})
        f = b('Тысяча восемсотъ пятьдесятъ восьмаго Года 20 Ноября въ Салантовскомъ Приходскомъ Римско-Католичесомъ Костелѣ '
              'Ксендзомъ Сташковскимъ окрещено дитя именемъ Магдалена со всѣми обрядами таинства.-')
        self.assertEqual((f['baptism_date'], f['priest'], f['child_name']), ('1858-11-20', 'Сташковскимъ', 'Магдалена'))
        f = b('Тысяча восемсотъ пятьдесятъ восьмаго года 1. Юня въ Салантовскомъ Приходскомъ Кастелѣ Кеняомъ Станковскимъ окрещено дитя')
        self.assertEqual((f['baptism_date'], f['priest']), ('1858-06-01', 'Станковскимъ'))
        f = b('Тысяча восемсотъ пятьдесятъ восьмаго года Іюля 22 дня въ Салантовскомъ Костелѣ Ксендзомъ Сташковскимъ окрещено')
        self.assertEqual(f['baptism_date'], '1858-07-22')

    def test_priest_after_altarist_onago_and_before_the_church(self):
        pe = module('parse_entries')
        b = lambda t: pe.parse({'baptism': t, 'parents': '', 'godparents': ''})['priest']
        self.assertEqual(b('года Мая девятаго дня - въ Плунгянскомъ Р.К. Прходскомъ Костелѣ, Аль таристомъ онаго Кс. Викентьемъ '
                           'Мараевичемъ окре щена дѣвица'), 'Викентьемъ Мараевичемъ')
        self.assertEqual(b('года Февраля двадцатага дня въ Плун гянскомъР. К. приходскомъ Костселѣ мѣстнымъ Кс. Воиткевичемъ '
                           'окрещена дитя именемъ'), 'Воиткевичемъ')
        self.assertEqual(b('года Мая востого дня Мѣстнымъ АльтаристомъКс Іоанномъ Контрымомъ въ Салантовскомъ Приходскимъ '
                           'Римеко Католическомъ Косте лѣ окрещенъ младенецъ'), 'Іоанномъ Контрымомъ')
        self.assertEqual(b('дня въ Плунгянскомъ Р.К. приходскомъ Костелѣ Викарнымъ онаго Кс. Людвикомъ Монтвидомъ окрещена девица'),
                         'Людвикомъ Монтвидомъ')
        self.assertEqual(b('дня въ Салантовскомъ Приходскомъ Р.К. Костелѣ Мѣстнымъ Викарнымъ Ксендзомъ Францишкомъ Климовичемъ '
                           'Окрещенъ младенецъ'), 'Францишкомъ Климовичемъ')

    def test_village_before_or_after_the_parish(self):
        pe = module('parse_entries')
        v = lambda t: pe.parse({'baptism': '', 'parents': t, 'godparents': ''})['village']
        self.assertEqual(v('Супруговъ дочь родившася 1861. года Декабря 18 днявъ деревни Жеймяхъ Салантовскаго Прихода. -'), 'Жеймяхъ')
        self.assertEqual(v('дочъ родившаяся сего года Марта четвертого дня вочскомъ, Салантовскаго Прихода въ Деревни Барацахъ. -'), 'Барацахъ')
        self.assertEqual(v('сынъ родившійся сего 1869 года Февраля 14.дня въ деревнѣ Кѣкштахъ сего прихоа. -'), 'Кѣкштахъ')
        self.assertEqual(v('Сынъ родившійся 1859 года Марта 5го дня въ деревни Имбогохъ Здѣшняго Прихода'), 'Имбогохъ')
        self.assertEqual(v('дочь 20 Ноября родилась въ дер. Имбаръ Салан товскаго Прихода. -'), 'Имбаръ')


class SingleReadingMerge(unittest.TestCase):
    def test_refuses_ids_of_another_book_and_demotes_doubtful_checked_lines(self):
        ms = module('merge_single_reading')
        props = {'0001_L1_baptism_01': {'scan': 1, 'row_id': '0001_L1', 'cell': 'baptism', 'bbox': [0, 0, 9, 9], 'split': 'train',
                                        'line': {'x': 5, 'slope': -0.03, 'band': [1, 8], 'core': [3, 6]}},
                 '0001_L1_baptism_02': {'scan': 1, 'row_id': '0001_L1', 'cell': 'baptism', 'bbox': [0, 9, 9, 18], 'split': 'train'}}
        with self.assertRaises(ValueError):
            ms.build([{'id': '0099_L9_baptism_01', 'text': 'x', 'status': 'draft', 'note': ''}], props, 'r', 'b')
        recs, demoted = ms.build([{'id': '0001_L1_baptism_01', 'text': 'Тысяча  восемсотъ', 'status': 'image_checked', 'note': ''},
                                  {'id': '0001_L1_baptism_02', 'text': '', 'status': 'image_checked', 'note': ''}], props, 'r', 'b')
        self.assertEqual([(x['status'], x['text']) for x in recs], [('image_checked', 'Тысяча восемсотъ'), ('rejected_crop', None)])
        self.assertEqual(demoted, ['0001_L1_baptism_02'])
        self.assertEqual(recs[0]['line']['slope'], -0.03)
        self.assertFalse(recs[0]['independent_verification'] or recs[0]['baseline_seen'])


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

    def test_year_words_1850s_1860s(self):
        iy = module('infer_years')
        self.assertEqual(iy.word_year('Тысяча восемьсотъ шестьдесятъ седьмаго года Декабря'), 1867)
        self.assertEqual(iy.word_year('Тысяча восемьсотъ пятьдесятъ девятаго года'), 1859)
        self.assertEqual(iy.word_year('Тысяча девятьсотъ третьяго года Января'), 1903)
        self.assertEqual(iy.digit_year('родившаяся 1867 года'), 1867)
