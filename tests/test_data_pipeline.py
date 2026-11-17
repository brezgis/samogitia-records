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


class RowsColumnsYearsMonths(unittest.TestCase):
    """Columns out of step and page turns in assemble_drafts.py, the previous year's tail in
    infer_years.py, and the month-order check of check_months.py (2026-11-16)."""

    @staticmethod
    def page(ad):
        made, queue = [], []

        def row(rid, scan, top, bottom, cells=None, **cols):
            queue.append({'row_id': rid, 'scan': scan, 'page': 'L', 'focal_y': [top, bottom], **({'cells': cells} if cells else {})})
            for cell, texts in cols.items():
                x = {'baptism': 100, 'parents': 600, 'godparents': 1100}[cell]
                for n, t in enumerate(texts):
                    y = top + 10 + 60 * n if isinstance(t, str) else t[0]
                    t = t if isinstance(t, str) else t[1]
                    made.append(({'id': f'{rid}_{cell}_{n + 1:02}', 'row_id': rid, 'scan': scan, 'cell': cell,
                                  'bbox': [x, y, x + 400, y + 50]}, t))

        def run(**kw):
            props, text_of = [p for p, _ in made], {p['id']: t for p, t in made}
            by_row, _, _ = ad.reassign(queue, props, text_of, split_missed=True, text_fold=True, repair=True, **kw)
            return {r: {c: ad.join_lines([text_of[p['id']] for p in ls if p['cell'] == c]) for c in ad.CELLS} for r, ls in by_row.items()}
        return row, run

    def test_entry_continues_over_the_page_turn(self):
        ad = module('assemble_drafts')
        row, run = self.page(ad)
        row('1_A', 1, 500, 1000, baptism=['Тысяча восемсотъ пятьдесятъ семаго Года', 'Августа перваго дня Викаріемъ Кс. Іоанномъ Монке-'],
            parents=['Крестьянъ Леонарда и Магдалены', 'дочь родившаяся 1 сего Августа'], godparents=['Воспріемниками были', 'Іосифъ Томашевски'])
        row('2_A', 2, 200, 500, baptism=['вичемъ окрещенъ младенецъ именемъ Барбара', 'со всѣми обрядами таинства.'],
            parents=['Салантовскаго Прихода въ деревнѣ Имбарехъ'], godparents=['-'])
        row('2_B', 2, 500, 1000, baptism=['Тысяча восемсотъ пятьдесятъ семаго Года', 'Августа второго дня окрещенъ младенецъ именемъ Іозефъ',
                                          'со всѣми обрядами таинства'],
            parents=['Крестьянъ Михала и Регины'], godparents=['Воспріемниками были'])
        row('3_A', 3, 200, 500, baptism=['окрещенъ младенецъ именемъ Янъ со всѣми обрядами'], parents=['Крестьянъ Яна и Анны'],
            godparents=['Воспріемниками были'])
        got = run()
        self.assertEqual(ad.reassign.folded_across, [['2_A', '1_A']])
        self.assertEqual(ad.reassign.continued, {'1_A': ['2_A']})
        self.assertTrue(got['1_A']['baptism'].endswith('Монкевичемъ окрещенъ младенецъ именемъ Барбара со всѣми обрядами таинства.'))
        self.assertTrue(got['1_A']['parents'].endswith('сего Августа Салантовскаго Прихода въ деревнѣ Имбарехъ'))
        # 3_A has lost its opening, but the baptism above it is complete and it opens its other columns: kept
        self.assertIn('3_A', got)
        self.assertEqual(got['2_B']['baptism'].count('окрещенъ'), 1)

    def test_right_page_one_column_off_is_refiled(self):
        ad = module('assemble_drafts')
        row, run = self.page(ad)
        off = {'baptism': [982, 443, 2228, 1044], 'parents': [3072, 468, 3902, 1069], 'godparents': [3902, 468, 4782, 1069]}
        ok = {'baptism': [1041, 420, 2309, 1000], 'parents': [2315, 480, 3180, 1060], 'godparents': [3180, 480, 4013, 1060]}
        self.assertTrue(ad.shifted_right_page({'cells': off}))
        self.assertFalse(ad.shifted_right_page({'cells': ok}))
        self.assertFalse(ad.shifted_right_page({}))
        row('A', 1, 400, 1000, cells=off, baptism=['Тысяча восемсотъ пятьдесятъ семаго Года', 'окрещенъ младенецъ именемъ Магдалена со всѣми обрядами'],
            parents=['Воспріемниками были', 'Крестьянинъ Игнатій Суркисъ'], godparents=['-'])
        got = run()
        self.assertEqual(ad.reassign.shifted, ['A'])
        self.assertEqual(got['A']['parents'], '')
        self.assertEqual(got['A']['godparents'], 'Воспріемниками были Крестьянинъ Игнатій Суркисъ')

    def test_columns_paired_by_openings_only_when_evenly_placed(self):
        ad = module('assemble_drafts')
        bap = ['Тысяча восемсотъ шестьдесятаго Года', 'окрещено дитя именемъ Іосифъ со всѣми обрядами Таинства']
        for base, lower, paired in ((330, 330, True), (0, 300, False)):
            row, run = self.page(ad)
            # the right page's entries begin `base` px below their baptisms (`lower` for the third entry, a short
            # row): its parents and godparents open in the layout row after it, which has no baptism opening
            row('A', 1, 400, 1000, baptism=bap, parents=[(410 + base, 'Крестьянъ Яна и Анны')],
                godparents=[(410 + base, 'Воспріемниками были Янъ')])
            row('B', 1, 1000, 1600, baptism=bap, parents=[(1010 + base, 'Крестьянъ Петра и Евы')],
                godparents=[(1010 + base, 'Воспріемниками были Петръ')])
            row('C', 1, 1600, 1900, baptism=bap[:1])
            row('C2', 1, 1900, 2500, baptism=[bap[1]], parents=[(1610 + lower, 'Крестьянъ Матеуша и Анны')],
                godparents=[(1610 + lower, 'Воспріемниками были Матеушъ')])
            row('D', 1, 2500, 3100, baptism=bap, parents=[(2510 + base, 'Крестьянъ Фомы и Розы')],
                godparents=[(2510 + base, 'Воспріемниками были Фома')])
            got = run()
            if paired:
                self.assertEqual(sorted(got), ['A', 'B', 'C', 'D'])
                self.assertEqual(got['C']['parents'], 'Крестьянъ Матеуша и Анны')
                self.assertEqual(got['C']['baptism'], ' '.join(bap))
                self.assertEqual(ad.reassign.out_of_step, {})
                self.assertIn('C', ad.reassign.paired_by_openings)
            else:
                # not one steady offset: the layout pairing stays, the side is flagged, the baptism is made whole
                self.assertEqual(ad.reassign.paired_by_openings, [])
                self.assertEqual(sorted(ad.reassign.out_of_step), ['A', 'B', 'C', 'C2', 'D'])
                self.assertEqual(got['C']['baptism'], ' '.join(bap))
                self.assertEqual(got['C2']['parents'], 'Крестьянъ Матеуша и Анны')
                self.assertEqual(got['C2']['baptism'], '')

    def test_twins_with_two_sets_of_godparents_are_not_out_of_step(self):
        ad = module('assemble_drafts')
        row, run = self.page(ad)
        bap = ['Тысяча восемсотъ пятьдесятъ семаго Года', 'окрещены со всѣми обрядами Таинства']
        row('A', 1, 400, 1000, baptism=bap, parents=['Крестьянъ Іозефа и Вероники', 'Сынъ и дочь родившіеся'],
            godparents=['Воспріемниками были Филипъ', 'съ Аполоніею', 'Воспріемниками были дочери'])
        row('B', 1, 1000, 1600, baptism=bap, parents=['Крестьянъ Петра и Евы'], godparents=['Воспріемниками были Петръ'])
        run()
        self.assertEqual(ad.reassign.out_of_step, {})

    def test_child_sex_against_the_parents_column(self):
        ad = module('assemble_drafts')
        self.assertEqual(ad.child_sex('окрещенъ младенецъ именемъ Анна Со всѣми обрядами'), 'f')
        self.assertEqual(ad.child_sex('окрещено дитя именемъ Казимиръ, со всѣми'), 'm')
        self.assertIsNone(ad.child_sex('именемъ Антони Со всѣми'))                 # -и: not judged
        self.assertIsNone(ad.child_sex('именемъ Марціян на, со всѣми'))           # a name the draft split
        self.assertIsNone(ad.child_sex('именами Барбара Магдалена со всѣми'))      # two names
        self.assertEqual(ad.parents_sex('законныхъ Супруговъ Сынъ родившійся 1857 года'), 'm')
        self.assertEqual(ad.parents_sex('супруговъ дочь родившаяся'), 'f')
        self.assertIsNone(ad.parents_sex('Супруговъ Сынъ и дочь родившіеся'))
        self.assertTrue(ad.baptism_finished('именемъ Янъ со всѣми обрядами Таиму'))
        self.assertFalse(ad.baptism_finished('Викарнымъ Ксендзомъ Францишкомъ Климовичемъ'))

    def test_previous_years_tail_at_the_start_of_a_book(self):
        iy = module('infer_years')
        self.assertEqual(iy.word_year('Тысяча Восемсотъ Пятьдесятъ Ше- стаго Года Ноября'), 1856)
        self.assertEqual(iy.word_year('Тысяча восемсотъ пятьдесятъ семаго Года Января'), 1857)
        self.assertEqual(iy.word_year('Тысяча восемсотъ шестьдесятаго Года Января'), 1860)
        self.assertEqual(iy.word_year('Тысяча восемьсотъ пятьдесятъ восьмаго года'), 1858)     # not "…сем…"
        queue, preds = [], {}

        def side(scan, texts):
            for i, t in enumerate(texts, 1):
                rid = f'{scan:04}_L{i}'
                queue.append({'row_id': rid, 'scan': scan, 'page': 'L', 'row_index': i, 'focal_y': [500 * i, 500 * i + 500]})
                preds[rid + '_b'] = {'id': rid + '_b', 'row_id': rid, 'cell': 'baptism', 'text': t}
        y56, y57, y58 = ('Тысяча восемсотъ пятьдесятъ %s года' % w for w in ('шестаго', 'семаго', 'восьмаго'))
        side(3, [y56, y56, 'Ноября двадцатаго дня', y56])                    # the old year's tail: 7 rows of 249
        side(4, [y56, 'Тысяча восемсотъ Оятьдесятъ шестаго года', y57, y57])  # the turn falls inside this side
        for scan in range(5, 35):
            side(scan, [y57] * 4)
        for scan in range(35, 65):
            side(scan, [y58] * 4)
        side(65, [y58])
        iy.infer(queue, preds)
        years = [q['register_year'] for q in queue]
        self.assertEqual(years[:8], [1856] * 6 + [1857] * 2)
        self.assertEqual((years.count(1856), years.count(1857), years.count(1858)), (6, 122, 121))
        # one stray "1856" among 1857 rows is not a year of its own
        queue2, preds2 = copy.deepcopy(queue[8:]), {k: v for k, v in preds.items() if int(k[:4]) >= 5}
        preds2['0005_L1_b'] = dict(preds2['0005_L1_b'], text=y56)
        iy.infer(queue2, preds2)
        self.assertNotIn(1856, {q['register_year'] for q in queue2})

    def test_month_order_fit(self):
        cm = module('check_months')

        def e(i, year, month, day=None, heading=None, birth=None, scan=None):
            f = {'baptism_month': {'value': month}, 'baptism_day': {'value': day},
                 'birth_month': {'value': birth and birth[0]}, 'birth_day': {'value': birth and birth[1]}}
            return {'row_id': f'{scan or 1 + i // 5:04}_L{i % 5 + 1}', 'scan': scan or 1 + i // 5, 'page': 'L', 'register_year': year,
                    'heading_month': heading, 'fields': f}
        # "Іюля" read as "Іюня" inside July, an unread month, the year turn, and a heading against the reading
        months = [6, 6, 7, 6, 7, 6, 7, None, 8, 12, 12, 1, 1]
        es = [e(i, 1897 if i < 11 else 1898, m, day=i + 1, birth=(m, i + 1) if m else None) for i, m in enumerate(months)]
        es[2]['heading_month'] = 7
        rows, summary = cm.check(es)
        self.assertEqual([r['fitted_month'] for r in rows], [6, 6, 7, 7, 7, 7, 7, 7, 8, 12, 12, 1, 1])
        self.assertEqual([r['row_id'] for r in rows if 'month_differs' in r['flags']], [es[3]['row_id'], es[5]['row_id']])
        self.assertEqual(summary['flags']['month_differs'], 2)
        # the heading outweighs the entry's own month
        es[2]['fields']['baptism_month']['value'] = 6
        rows, _ = cm.check(es)
        self.assertEqual(rows[2]['fitted_month'], 7)
        self.assertIn('month_differs', rows[2]['flags'])
        # births: later than the baptism, the month after (a misreading), long before; a scan where they all disagree
        es = [e(0, 1857, 5, day=8, birth=(5, 9), scan=30), e(1, 1857, 5, day=9, birth=(6, 2), scan=31),
              e(2, 1857, 5, day=11, birth=(5, 11), scan=31), e(3, 1857, 5, day=12, birth=(4, 30), scan=32),
              e(4, 1857, 5, day=13, birth=(1, 3), scan=33)]
        es += [e(5 + i, 1857, 11, day=18 + i, birth=(5, 1 + i), scan=34) for i in range(4)]
        rows, summary = cm.check(es)
        self.assertEqual([r['flags'] for r in rows[:5]], [['birth_after_baptism'], ['birth_after_baptism', 'birth_month_misread'], [], [],
                                                         ['birth_long_before']])
        self.assertEqual([d['scan'] for d in summary['scans_where_columns_disagree']], [34])
        self.assertTrue(all('scan_columns_disagree' in r['flags'] for r in rows[5:]))


class MonthTownshipFixesAndFieldTagger(unittest.TestCase):
    """parse_entries.py: "Мая" inside other words, "волости" inside surnames; neural_parser/combine.py:
    rules and tagger combined per field (synthetic spans: the tests need no model and no torch)."""
    pe = module('parse_entries')

    def parents(self, text, year=1898):
        return self.pe.parse({'baptism': '', 'parents': text, 'godparents': '', 'register_year': year})

    def test_may_is_not_read_inside_the_verb_or_another_month(self):
        # "родивш-аяс-я" holds an "ая"; the real month is one letter off ("Іюмя" for "Іюня"/"Іюля")
        f = self.parents('Крестьянъ Плунгянской волости Яна и Анны изъ Петкусовъ Стонкусовъ законныхъ супруговъ дочь '
                         'родившаяся сего 1898 года Іюня 18 дня, въ м. Плунгянахъ')
        self.assertEqual((f['birth_month'], f['birth_day']), (6, 18))
        f = self.parents('Крестьянъ Яна и Анны урожденной Петковны Стонкусовъ законныхъ супруговъ дочь родившаяся '
                         '1854 года Декабугя 22 дня въ Деревни Кулѣ Плунгянскаго прихода')
        self.assertEqual((f['birth_month'], f['birth_day']), (12, 22))
        b = self.pe.parse({'baptism': 'Тысяча восемьсотъ семьдесятаго года Наября пятага дня въ Плунгянскомъ Р.К. Костелѣ',
                           'parents': '', 'godparents': ''})
        self.assertEqual((b['baptism_month'], b['baptism_day']), (11, 5))
        b = self.pe.parse({'baptism': 'Тысяча восемьсотъ шестаго года Мауста перваго дня въ Плунгянскомъ', 'parents': '', 'godparents': ''})
        self.assertNotEqual(b['baptism_month'], 5)

    def test_may_itself_is_still_read_exact_or_as_a_word_of_its_own(self):
        for text, day in (('сынъ родившійся 1898 года Мая 19 дня въ деревнѣ Кулѣ', 19), ('сынъ родившійся 1886 года сая 6 дня въ деревни Кули', 6),
                          ('дочь родившаяся 1857 Года Мася 2. дня въ Местечки Плунгянахъ', 2), ('сынъ родившійся 15 мая 1904 года въ дер. Кули', 15),
                          ('сынъ родившійся 1892 года 28 каявъ дер. Кули', 28)):
            f = self.parents(text)
            self.assertEqual((f.get('birth_month'), f.get('birth_day')), (5, day), text)
        b = self.pe.parse({'baptism': 'Тысяча восемьсотъ перваго года Ма семьнадцатаго дня въ Плунгянскомъ', 'parents': '', 'godparents': ''})
        self.assertEqual((b['baptism_month'], b['baptism_day']), (5, 17))

    def test_unreadable_month_keeps_the_day_and_gives_no_month(self):
        f = self.parents('Крестьянъ Яна и Анны урожденной Петковны Стонкусовъ законныхъ супруговъ сынъ родившійся 1854 года Іюмья 22 дня '
                         'въ Деревни Кулѣ Плунгянскаго прихода', 1854)
        self.assertEqual((f.get('birth_month'), f.get('birth_day'), f.get('birth_date')), (None, 22, None))
        b = self.pe.parse({'baptism': 'Тысяча девятьсотъ шестаго года Таромя четвертаго дня въ Плунгянскомъ Р. К. Костелѣ',
                           'parents': '', 'godparents': ''})
        self.assertEqual((b['baptism_month'], b['baptism_day'], b['baptism_date']), (None, 4, None))

    def test_township_word_is_not_found_in_a_surname(self):
        # older wording, no township: "Волонтовны" / "Воловскихъ" used to be taken for "волости"
        f = self.parents('Крестьянъ Казимира и Барбары урожденной Самутовны Волонтовъ законныхъ Супруговъ сынъ родившійся '
                         '1857 года Марта 5 дня въ деревни Жеймяхъ Салантовскаго Прихода', 1857)
        self.assertIsNone(f['township'])
        self.assertEqual((f['father'], f['mother'], f['maiden_and_surname']), ('Казимира', 'Барбары', 'Самутовны Волонтовъ'))
        # later wording, "вол." misread: the surname after "изъ" is not the anchor either
        f = self.parents('Крестьянъ Бернатовской вос. Игнатія и Антонины изъ Виркисовъ Воловскихъ закон. супруг. дочь '
                         'родившаяся 26 Іюня 1902 года въ дер. Кули')
        self.assertEqual((f['township'], f['father'], f['mother'], f['maiden_and_surname']),
                         ('Бернатовской', 'Игнатія', 'Антонины', 'Виркисовъ Воловскихъ'))

    def test_township_abbreviation_ends_before_the_fathers_name(self):
        f = self.parents('Крестьянъ Плунгянской вол. Станислава и Анны изъ Салисовъ Даукшасовъ закон. супруг. дочь '
                         'родившаяся 12 Марта 1902 г. въ дер. Кули')
        self.assertEqual((f['township'], f['father'], f['birth_date']), ('Плунгянской', 'Станислава', '1898-03-12'))
        f = self.parents('Крестьянъ Плунгянской волости Яна и Анны изъ Салисовъ Даукшасовъ законныхъ супруговъ сынъ')
        self.assertEqual((f['township'], f['father'], f['mother']), ('Плунгянской', 'Яна', 'Анны'))

    # ---- the combination
    ENTRY = {'row_id': 'x', 'register_year': 1858,
             'baptism': 'Тысяча восемсотъ пятьдесятъ осьмаго года Марта 5 дня въ Салантовскомъ Р.К. Костелѣ Кс. Іоанномъ Контримомъ '
                        'окрещенъ младенецъ именемъ Іосифъ со всѣми обрядами таинства',
             'parents': 'Крестьянъ Казимира и Барбары урожденной Самутовны Меш кисовъ законныхъ Супруговъ сынъ ромилея '
                        'сего года Марта 3 дня въ деревни Жеймяхъ Салантовскаго Прихода',
             'godparents': 'Воспріемниками были Крестьянинъ Іосифъ Самутисъ съ Анною Петра Можейки женою'}

    def combine(self):
        import sys
        sys.path.insert(0, str(ROOT / 'pipeline' / 'neural_parser'))
        sys.path.insert(0, str(ROOT / 'pipeline'))
        import combine
        return combine

    def span(self, col, words, conf):
        t = self.ENTRY[col]
        s = t.index(words)
        return {'s': s, 'e': s + len(words), 'conf': conf}

    def tags(self, low=0.99):
        return {'baptism': {'CHILD': self.span('baptism', 'Іосифъ', 0.99), 'PRIEST': self.span('baptism', 'Кс. Іоанномъ Контримомъ', 0.9)},
                'parents': {'FATHER': self.span('parents', 'Казимира', 0.99), 'MOTHER': self.span('parents', 'Барбары', 0.99),
                            'MAIDEN': self.span('parents', 'Самутовны', 0.98), 'SURNAME': self.span('parents', 'Меш кисовъ', 0.6),
                            'TOWNSHIP': self.span('parents', 'Самутовны', 0.9), 'VILLAGE': self.span('parents', 'Жеймяхъ', low),
                            'BIRTH_DATE': self.span('parents', 'сего года Марта 3 дня', 0.97)},
                'godparents': {'GODFATHER': self.span('godparents', 'Іосифъ Самутисъ', 0.99), 'GODMOTHER': self.span('godparents', 'Анною', 0.95),
                               'GM_STATUS': self.span('godparents', 'Петра Можейки женою', 0.95)}}

    def test_agreement_tagger_and_threshold(self):
        cb = self.combine()
        f = cb.combine_entry(self.ENTRY, self.tags())['fields']
        self.assertEqual((f['father']['value'], f['father']['by']), ('Казимира', 'both'))
        self.assertEqual((f['child_name']['value'], f['child_name']['by']), ('Іосифъ', 'both'))
        # the rules' last-word split gives "кисовъ"; the tagger has the whole divided surname, and the
        # family surname is taken from 0.5 up
        self.assertEqual((f['family_surname']['value'], f['family_surname']['by']), ('Меш кисовъ', 'tagger'))
        self.assertEqual(f['family_surname']['alt'], {'value': 'кисовъ', 'by': 'rules'})
        self.assertEqual(f['maiden_and_surname'], {'value': 'Самутовны Меш кисовъ', 'by': 'rules'})      # the old field is the rules' own
        # a formula word trimmed: the rules keep "Крестьянинъ" before the godfather
        self.assertEqual((f['godfather']['value'], f['godfather']['by']), ('Іосифъ Самутисъ', 'both'))
        self.assertEqual(f['godmother']['value'], 'Анною')
        self.assertEqual(f['godmother_status']['value'], 'Петра Можейки женою')
        self.assertTrue(f['godparents']['value'].startswith('Крестьянинъ Іосифъ Самутисъ'))
        # below the threshold the rules' value stays and the tagger's becomes the alternative
        t = self.tags()
        t['parents']['FATHER'] = self.span('parents', 'Барбары', 0.55)
        f = cb.combine_entry(self.ENTRY, t)['fields']
        self.assertEqual((f['father']['value'], f['father']['by'], f['father']['alt']['value']), ('Казимира', 'rules', 'Барбары'))
        t['parents']['FATHER'] = self.span('parents', 'Барбары', 0.93)
        f = cb.combine_entry(self.ENTRY, t)['fields']
        self.assertEqual((f['father']['value'], f['father']['by'], f['father']['alt']), ('Барбары', 'tagger', {'value': 'Казимира', 'by': 'rules'}))

    def test_township_dates_priest_and_missing_spans(self):
        cb = self.combine()
        out = cb.combine_entries([self.ENTRY], [self.tags()])[0]['fields']
        # no "волости" in the text: no township, and the tagger's is not even an alternative
        self.assertEqual(out['township'], {'value': None, 'by': 'none'})
        # the rules find no "родивш..." (misread "ромилея"); the tagger's phrase is decoded with the rules' own tables
        self.assertEqual((out['birth_month']['value'], out['birth_day']['value'], out['birth_day']['by']), (3, 3, 'tagger'))
        self.assertEqual(out['birth_date']['value'], '1858-03-03')
        self.assertEqual((out['baptism_date']['value'], out['baptism_date']['by']), ('1858-03-05', 'rules'))
        self.assertEqual((out['priest']['value'], out['priest']['by']), ('Іоанномъ Контримомъ', 'both'))
        t = self.tags()
        t['baptism']['PRIEST'] = self.span('baptism', 'Контримомъ', 0.99)
        self.assertEqual(cb.combine_entry(self.ENTRY, t, priest='rules')['fields']['priest']['value'], 'Іоанномъ Контримомъ')
        # an entry without usable spans is the rules alone, with the new fields from the rules' own split
        f = cb.combine_entry(self.ENTRY, None)['fields']
        rules = self.pe.parse(self.ENTRY)
        for k, v in rules.items():
            self.assertEqual(f[k]['value'], v, k)
        self.assertEqual((f['maiden_name']['value'], f['family_surname']['value'], f['family_surname']['by']), ('Самутовны Меш', 'кисовъ', 'rules'))
        self.assertTrue(all(v['by'] in ('rules', 'none') for v in f.values()))

    def test_spans_of_another_draft_version_are_refused(self):
        import tempfile
        cb = self.combine()
        e = self.ENTRY
        row = {'row_id': 'x', 'hash': {c: cb.text_hash(e[c]) for c in ('baptism', 'parents', 'godparents')},
               'spans': [{'col': 'parents', 'field': 'FATHER', **self.span('parents', 'Казимира', 0.99)}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'tagger_spans.json'
            p.write_text(json.dumps({'model': 'm', 'entries': [row]}))
            tags, info = cb.load_spans(p, [e])
            self.assertEqual((info['stale'], tags[0]['parents']['FATHER']['s']), (0, e['parents'].index('Казимира')))
            changed = dict(e, parents=e['parents'].replace('Казимира', 'Казиміра'))
            tags, info = cb.load_spans(p, [changed, dict(e, row_id='y')])
            self.assertEqual((info['stale'], tags), (2, [None, None]))

    def test_every_field_keeps_value_and_readers_see_the_old_keys(self):
        cb = self.combine()
        f = cb.combine_entry(self.ENTRY, self.tags())['fields']
        for k in list(self.pe.parse(self.ENTRY)) + ['maiden_name', 'family_surname', 'godfather', 'godmother', 'godmother_status']:
            self.assertIn('value', f[k], k)
            self.assertIn(f[k]['by'], ('rules', 'tagger', 'both', 'none'), k)
        self.assertIsInstance(f['birth_month']['value'], int)
        # reconcile_surnames.draft_surname reads the last word of the unchanged old field
        rs = module('reconcile_surnames')
        self.assertEqual(rs.draft_surname(f), 'кисовъ')

    def test_day_digits_and_day_words_beside_a_misread_month(self):
        # "13 Юня": the "3" is the day's second digit, not the month's first letter (the day used to be 1);
        # "207юня", "100ктября": the digit written onto the name is its misread first letter
        for text, date in (('дочь 13 Юня родилась въ деревни Кули', (6, 13)), ('сынъ родившійся 207юня 1905 года въ деревни Кули', (6, 20)),
                           ('дочь родившаяся 100ктября 1900 г. въ деревни Кули', (10, 10)), ('сынъ родившійся 17 прѣля 1900 года въ дер. Кули', (4, 17))):
            f = self.parents(text)
            self.assertEqual((f.get('birth_month'), f.get('birth_day')), date, text)
        day = lambda b: self.pe.parse({'baptism': b, 'parents': '', 'godparents': ''}).get('baptism_day')
        # the unreadable month ran into the day, or the day's own words must not be dropped
        self.assertEqual(day('Тысяча восемсотъ четвертаго года Іомядвадцатъ девятаго дня въ Плунгянскомъ'), 29)
        self.assertEqual(day('Тысяча восемсотъ третьяго гада Масячетвер таго дня въ Плунгянскомъ'), 4)
        self.assertEqual(day('Тысяча восемсотъ второго года Апрнъ го мя восмаго дня въ Плунгянскомъ'), 8)
        self.assertIsNone(day('Тысяча восемсотъ второго года Ігоня двадезатъ мстаго дня въ Плунгянскомъ'))
        self.assertEqual(day('Тысяча восемсотъ пятьдесятъ шестого года Декабря двадцать востого дня въ Салантовскомъ'), 28)

    def test_the_combination_decodes_a_date_as_the_rules_do(self):
        cb = self.combine()
        from common import decode_date
        # the experiment's decoder (kept for its day checks) finds "Мая" in other words; the strict one does not
        self.assertEqual(decode_date('1854 года Іюмья 22 дня'), (5, 22))
        self.assertEqual(decode_date('1854 года Іюмья 22 дня', strict=True), (None, None))
        self.assertEqual(decode_date('Тысяча восемсотъ пятьдесятъ восьмаго года Наября пятаго дня', strict=True), (11, 5))
        self.assertEqual(decode_date('10 Мая 1900 года', strict=True), (5, 10))
        e = dict(self.ENTRY, parents=self.ENTRY['parents'].replace('сего года Марта 3 дня', 'сего года Іюмья 3 дня'))
        t = self.tags()
        t['parents']['BIRTH_DATE'] = {'s': e['parents'].index('сего года'), 'e': e['parents'].index('3 дня') + 5, 'conf': 0.99}
        f = cb.combine_entry(e, t)['fields']
        self.assertIsNone(f['birth_month']['value'])
        self.assertNotIn('birth_date', {k for k, v in f.items() if v['value']})
