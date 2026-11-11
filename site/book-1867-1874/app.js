(() => {
const SPREADS = window.SPREADS, INDEX = window.INDEX, $ = (s, r = document) => r.querySelector(s);
const body = document.body, book = $('#book'), block = $('#block');
const LOCALE = { en: 'en-GB', lt: 'lt-LT', pl: 'pl-PL', ru: 'ru-RU' };
/* which book this is (book.js) and the shelf it stands on (../library.js); both written by site/make_library.py */
const BK = window.BOOK || { parish: 'plunge', dir: 'book', years: [1886, 1890], archive: '1827/1/23', scan: 93, row: '0093_R3' };
const LIB = window.LIBRARY || { parishes: [] };
const PARISH = LIB.parishes.find(p => p.id === BK.parish) || { id: 'plunge', books: [], names: {
  en: { name: 'Plungė', county: 'Telšiai' }, lt: { name: 'Plungė', gen: 'Plungės', countyGen: 'Telšių' },
  pl: { name: 'Płungiany', loc: 'Płungianach', lay: 'leżały', countyLoc: 'telszewskim' },
  ru: { name: 'Плунге', adjNom: 'Плунгянский', adjGen: 'Плунгянского', was: 'входило', county: 'Тельшевский' } } };
const Y0 = BK.years[0], Y1 = BK.years[1], YMID = Math.floor((Y0 + Y1) / 2), LATE = Y1 > 1900;
const T = {
  en: { title: 'Žemaičių metrikai', sub: 'Parish registers of Samogitia. Plungė, baptisms, January 1888',
    namesH: "Names", names1: "A name can appear here in three forms: the Russian letters the machine read from the page, a rendering of them into the language you are reading, and, in the margin, the family name as the clerk wrote it a second time. These are readings and renderings, not identifications. Two entries with the same name are not thereby the same person, and the search finds spellings that look alike without claiming they are one family.", dataLine: "The readings, the translations and the recognition model are open: <a href=\"https://github.com/brezgis/samogitia-records\">data and code</a>, <a href=\"https://huggingface.co/brezgis/samogitia-plunge-htr\">model</a>.",
    aboutH: 'About these registers',
    about1: 'From baptism to burial, a Catholic life in Samogitia was written into the parish books. Every parish kept registers, metrikai in Lithuanian, of baptisms, marriages and deaths. This is one of them: the baptisms of Plungė parish, in the diocese of Samogitia, for 1886 to 1890.',
    about2: 'In 1888 Plungė lay in the Russian Empire, in Telšiai county of Kovno governorate, and the registers had to be kept in Russian. So the priest wrote Lithuanian and Polish names in Russian letters, into a printed Russian form, and dated them by the old Julian calendar, twelve days behind the one we use.',
    readH: 'Reading an entry',
    read1: 'Every entry repeats one formula across three columns: when, where and by whom the child was baptised; who the parents were, their estate and district, and when and where the child was born; and who the godparents were. Family names stand as the formula puts them, “of the Takiovs”, so here they often end in -ov where the family itself would have said -is, -as or -us.',
    read2: "The handwriting was read by a recognition model trained on about 2,300 lines of these registers, each read independently by two AI readers and checked against each other, then translated by machine. No person has checked the result. Ordinary words come out well; names and villages often do not.",
    colsH: "The printed columns", cols: [["Прозваніе крещаемыхъ", "Surname of the baptised, written sideways in the margin"], ["№", "Entry number"], ["Число рожденія / крещенія", "Day of birth / day of baptism"], ["Когда, гдѣ, кто и кѣмъ … окрещенъ?", "When, where, who and by whom was baptised, with water only or with all the rites?"], ["Какихъ родителей …?", "Of which parents, of which estate or community; when and where the child was born"], ["Кто были … воспріемниками …?", "Who, by name and surname, were the godparents, and who was present"], ["Рукоприкладство свидѣтелей …", "Signatures of witnesses, if desired"]],
    sideMargin: "In the margin", sideDiffer: x => `The machine read the surname inside the entry as “${x}”; the margin is the better reading.`, sideNo: "No.", sideBorn: "born", sideBapt: "baptised", sideNote: "Later note", sexM: "boy", sexF: "girl", sideBy: "Side columns read once by machine.",
    heads: {"margin": "Surname of the baptised", "no": "No.", "dates": "Day of birth / baptism", "baptism": "When, where, by whom baptised", "parents": "Parents, estate; when and where born", "godparents": "Godparents and those present", "sign": "Witnesses’ signatures"},
    clothType: { skara: 'wool shawl', lovatiesė: 'bedspread' },
    clothH: 'The cloth and the ribbon',
    cloth1: 'The cover and the ribbon are real Samogitian textiles in the National Museum of Lithuania. The museum’s photographs are used under CC BY 4.0.',
    
    ph: 'Name, village or date, 1886 to 1890', chooseH: 'Choose an entry', chooseP: 'Point at a row of the register to read it. Click to keep it open.',
    everyH: 'The whole page, translated', everyP: 'Rest the pointer on a sheet to see the handwriting under it, or choose an entry for its notes.',
    bapt: 'Baptised', born: 'born', marks: 'The ribbon marks this entry.', move: 'Move the ribbon here', from: 'Read from: ',
    key: '<span class="u">Dotted</span> marks a reading the machine was unsure of; <span class="ed">[italic brackets]</span> are its remarks. Rest the pointer on a name to see the Russian it was read from.',
    warn: 'Read and translated by machine; nobody has checked it. Trust the handwriting over the translation.',
    sources: 'Sources', register: 'Register: Roman Catholic parish of Plungė, births and baptisms 1886–1890, Lithuanian State Historical Archives, 1827/1/23, from <a href="https://www.epaveldas.lt/">epaveldas.lt</a> (non-commercial use).',
    museum: 'National Museum of Lithuania', showR: 'Show the right-hand page', showL: 'Show the left-hand page',
    none: 'Nothing close to that. Try fewer letters; spellings in the register vary a lot.', noName: 'name not read', noDate: 'date not read',
    found: n => n === 1 ? '1 entry' : `${n} entries`, more: n => `Showing the first ${n}.`, away: 'Greyed entries are on pages not bound into this sample yet.',
    tips: 'Try a name in any spelling, a village, or a date such as “10 January 1888”, “03.1887” or “#8”.',
    no: 'no.', scan: 'scan', onDate: 'baptised or born', anyText: 'matching', entryNo: 'entry number', and: 'and',
    cloth: { plunge: 'Cover cloth: wool and linen bedspread (divonas), late 19th century, Palūščiai village, Plungė district', kretinga: 'Cover cloth: striped wool shawl, second half of the 19th century, Budriai village, Kretinga district', telsiai: 'Cover cloth: tapestry-woven bedspread (divonas), late 19th century, Vaštakiai village, Telšiai district' },
    ribbon: { mazeikiai: 'Ribbon: braided wool sash, 1930, Meinoriai village, Mažeikiai district', taurage: 'Ribbon: round-braided wool sash, late 19th century, Tauragė district', ukrinai: 'Ribbon: braided wool garter sash, about 1940, Ukrinai village, Mažeikiai district' } },
  lt: { title: 'Žemaičių metrikai', sub: 'Žemaitijos parapijų knygos. Plungė, krikštai, 1888 m. sausis',
    namesH: "Vardai ir pavardės", names1: "Vardas čia gali būti užrašytas trimis pavidalais: rusiškomis raidėmis, kurias mašina perskaitė puslapyje, jų perrašu ta kalba, kuria skaitote, ir paraštėje – pavarde, kurią raštininkas užrašė antrą kartą. Tai skaitymai ir perrašai, o ne tapatybės nustatymas. Du įrašai su ta pačia pavarde dar nereiškia to paties žmogaus, o paieška randa panašias rašybas, netvirtindama, kad tai viena šeima.", dataLine: "Skaitymai, vertimai ir atpažinimo modelis yra atviri: <a href=\"https://github.com/brezgis/samogitia-records\">duomenys ir kodas</a>, <a href=\"https://huggingface.co/brezgis/samogitia-plunge-htr\">modelis</a>.",
    aboutH: 'Apie šias knygas',
    about1: 'Nuo krikšto iki laidotuvių Žemaitijos kataliko gyvenimas buvo užrašomas parapijos knygose. Kiekviena parapija vedė krikšto, santuokos ir mirties metrikus. Čia viena tokių knygų: Žemaičių vyskupijos Plungės parapijos krikšto metrikai, 1886–1890 m.',
    about2: '1888 m. Plungė priklausė Rusijos imperijai, Kauno gubernijos Telšių apskričiai, ir metrikus reikėjo rašyti rusiškai. Todėl kunigas lietuviškus ir lenkiškus vardus rašė rusiškomis raidėmis į spausdintą rusišką formą, o datas žymėjo pagal senąjį Julijaus kalendorių, dvylika dienų atsiliekantį nuo dabartinio.',
    readH: 'Kaip skaityti įrašą',
    read1: 'Kiekvienas įrašas kartoja tą pačią formulę trijose skiltyse: kada, kur ir kas pakrikštijo vaiką; kas tėvai, koks jų luomas ir valsčius, kada ir kur vaikas gimė; kas buvo krikštatėviai. Pavardės užrašytos taip, kaip reikalauja formulė, daugiskaitos kilmininku, todėl čia jos dažnai baigiasi -ov, nors pati šeima būtų sakiusi -is, -as ar -us.',
    read2: "Rankraštį perskaitė atpažinimo modelis, apmokytas maždaug 2 300 šių knygų eilučių, kurias nepriklausomai perskaitė ir sulygino du dirbtinio intelekto skaitytojai; vertimas – mašininis. Žmogus rezultato netikrino. Įprasti žodžiai perskaitomi gerai, vardai ir kaimai – dažnai klaidingai.",
    colsH: "Spausdinti stulpeliai", cols: [["Прозваніе крещаемыхъ", "Krikštijamųjų pavardė, įrašyta paraštėje skersai"], ["№", "Įrašo numeris"], ["Число рожденія / крещенія", "Gimimo diena / krikšto diena"], ["Когда, гдѣ, кто и кѣмъ … окрещенъ?", "Kada, kur, kas ir kieno pakrikštytas – tik vandeniu ar su visomis apeigomis?"], ["Какихъ родителей …?", "Kokių tėvų, kokio luomo ar bendruomenės; kada ir kur gimė vaikas"], ["Кто были … воспріемниками …?", "Kas, nurodant vardą ir pavardę, buvo krikštatėviai ir kas dalyvavo"], ["Рукоприкладство свидѣтелей …", "Liudytojų parašai (pagal pageidavimą)"]],
    sideMargin: "Paraštėje", sideDiffer: x => `Įrašo tekste mašina pavardę perskaitė „${x}“; paraštės skaitymas patikimesnis.`, sideNo: "Nr.", sideBorn: "gimė", sideBapt: "pakrikštyta(s)", sideNote: "Vėlesnė pastaba", sexM: "berniukas", sexF: "mergaitė", sideBy: "Šoniniai stulpeliai perskaityti mašinos vieną kartą.",
    heads: {"margin": "Krikštijamųjų pavardė", "no": "Nr.", "dates": "Gimimo / krikšto diena", "baptism": "Kada, kur, kas pakrikštijo", "parents": "Tėvai, luomas; kada ir kur gimė", "godparents": "Krikštatėviai ir dalyvavusieji", "sign": "Liudytojų parašai"},
    clothType: { skara: 'vilnonė skara', lovatiesė: 'lovatiesė' },
    clothH: 'Audinys ir juostelė',
    cloth1: 'Viršelis ir juostelė – tikri žemaitiški audiniai iš Lietuvos nacionalinio muziejaus rinkinių. Muziejaus nuotraukos naudojamos pagal CC BY 4.0 licenciją.',
    
    ph: 'Vardas, kaimas arba data, 1886–1890 m.', chooseH: 'Pasirinkite įrašą', chooseP: 'Užveskite pelę ant knygos eilutės, kad ją perskaitytumėte. Spustelėkite, kad liktų atversta.',
    everyH: 'Visas puslapis, išverstas', everyP: 'Užveskite pelę ant lapelio, kad pamatytumėte rankraštį po juo, arba pasirinkite įrašą.',
    bapt: 'Krikštas', born: 'gimimas', marks: 'Juostelė žymi šį įrašą.', move: 'Perkelti juostelę čia', from: 'Perskaityta iš: ',
    key: '<span class="u">Taškuota linija</span> žymi vietas, dėl kurių mašina nebuvo tikra; <span class="ed">[kursyvas skliaustuose]</span> – jos pastabos. Užvedę pelę ant vardo, matysite rusišką užrašą, iš kurio jis perskaitytas.',
    warn: 'Perskaityta ir išversta mašinos; niekas netikrino. Pasikliaukite rankraščiu, ne vertimu.',
    sources: 'Šaltiniai', register: 'Metrikų knyga: Plungės Romos katalikų parapijos gimimo ir krikšto metrikai, 1886–1890 m., Lietuvos valstybės istorijos archyvas, 1827/1/23, iš <a href="https://www.epaveldas.lt/">epaveldas.lt</a> (nekomerciniam naudojimui).',
    museum: 'Lietuvos nacionalinis muziejus', showR: 'Rodyti dešinįjį puslapį', showL: 'Rodyti kairįjį puslapį',
    none: 'Nieko panašaus nerasta. Pabandykite mažiau raidžių: rašyba knygoje labai įvairuoja.', noName: 'vardas neperskaitytas', noDate: 'data neperskaityta',
    found: n => `Įrašų: ${n}`, more: n => `Rodoma pirmi ${n}.`, away: 'Pilki įrašai yra puslapiuose, kurie dar neįrišti į šį pavyzdį.',
    tips: 'Rašykite vardą bet kokia rašyba, kaimą arba datą, pvz., „1888 sausio 10“, „03.1887“ ar „#8“.',
    no: 'nr.', scan: 'skenas', onDate: 'krikštyta arba gimė', anyText: 'atitinka', entryNo: 'įrašo numeris', and: 'ir',
    cloth: { plunge: 'Viršelio audinys: vilnos ir lino lovatiesė (divonas), XIX a. pab., Palūščių k., Plungės r.', kretinga: 'Viršelio audinys: dryžuota vilnonė skara, XIX a. II p., Budrių k., Kretingos r.', telsiai: 'Viršelio audinys: kiliminio audimo lovatiesė (divonas), XIX a. pab., Vaštakių k., Telšių r.' },
    ribbon: { mazeikiai: 'Juostelė: pintinė vilnonė juosta, 1930 m., Meinorių k., Mažeikių r.', taurage: 'Juostelė: apvaliai pinta vilnonė juosta, XIX a. pab., Tauragės r.', ukrinai: 'Juostelė: pintinė vilnonė juosta-keliaraištis, apie 1940 m., Ukrinų k., Mažeikių r.' } },
  pl: { title: 'Žemaičių metrikai', sub: 'Księgi parafialne Żmudzi. Płungiany, chrzty, styczeń 1888',
    namesH: "Imiona i nazwiska", names1: "Nazwisko może tu występować w trzech postaciach: rosyjskimi literami, które maszyna odczytała ze strony, w transkrypcji na język, w którym czytasz, oraz na marginesie – jako nazwisko rodziny zapisane przez pisarza po raz drugi. To odczyty i transkrypcje, a nie identyfikacje. Dwa wpisy z tym samym nazwiskiem nie oznaczają jeszcze tej samej osoby, a wyszukiwarka znajduje podobne pisownie, nie twierdząc, że to jedna rodzina.", dataLine: "Odczyty, tłumaczenia i model rozpoznawania są otwarte: <a href=\"https://github.com/brezgis/samogitia-records\">dane i kod</a>, <a href=\"https://huggingface.co/brezgis/samogitia-plunge-htr\">model</a>.",
    aboutH: 'O tych księgach',
    about1: 'Od chrztu po pogrzeb życie katolika na Żmudzi zapisywano w księgach parafialnych. Każda parafia prowadziła metryki chrztów, ślubów i zgonów. To jedna z nich: metryki chrztów parafii Płungiany w diecezji żmudzkiej za lata 1886–1890.',
    about2: 'W 1888 roku Płungiany leżały w Cesarstwie Rosyjskim, w powiecie telszewskim guberni kowieńskiej, a metryki należało prowadzić po rosyjsku. Ksiądz zapisywał więc litewskie i polskie imiona i nazwiska rosyjskimi literami w drukowanym rosyjskim formularzu i datował je według dawnego kalendarza juliańskiego, o dwanaście dni wcześniejszego od dzisiejszego.',
    readH: 'Jak czytać wpis',
    read1: 'Każdy wpis powtarza jedną formułę w trzech kolumnach: kiedy, gdzie i kto ochrzcił dziecko; kim byli rodzice, jakiego stanu i z jakiej gminy, kiedy i gdzie dziecko się urodziło; kto był rodzicami chrzestnymi. Nazwiska stoją tak, jak wymaga formuła, w dopełniaczu liczby mnogiej, dlatego często kończą się tu na -ow, choć sama rodzina powiedziałaby -is, -as albo -us.',
    read2: 'Pismo odczytał model rozpoznawania wytrenowany na około 2300 wierszach tych ksiąg, z których każdy przeczytało niezależnie dwóch czytelników AI i porównano ich odczyty; tłumaczenie jest maszynowe. Nikt nie sprawdzał wyniku. Zwykłe słowa wychodzą dobrze, nazwiska i nazwy wsi często nie.',
    colsH: 'Drukowane rubryki', cols: [["Прозваніе крещаемыхъ", "Nazwisko ochrzczonego, pisane bokiem na marginesie"], ["№", "Numer wpisu"], ["Число рожденія / крещенія", "Dzień urodzenia / dzień chrztu"], ["Когда, гдѣ, кто и кѣмъ … окрещенъ?", "Kiedy, gdzie, kto i przez kogo został ochrzczony, tylko z wody czy ze wszystkimi obrzędami?"], ["Какихъ родителей …?", "Z jakich rodziców, jakiego stanu lub gminy; kiedy i gdzie urodziło się dziecko"], ["Кто были … воспріемниками …?", "Kto z imienia i nazwiska był rodzicami chrzestnymi i kto był obecny"], ["Рукоприкладство свидѣтелей …", "Podpisy świadków, według życzenia"]],
    sideMargin: "Na marginesie", sideDiffer: x => `W treści wpisu maszyna odczytała nazwisko jako „${x}”; odczyt z marginesu jest pewniejszy.`, sideNo: "Nr", sideBorn: "ur.", sideBapt: "ochrzcz.", sideNote: "Późniejsza adnotacja", sexM: "chłopiec", sexF: "dziewczynka", sideBy: "Boczne rubryki odczytane raz przez maszynę.",
    heads: {"margin": "Nazwisko ochrzczonego", "no": "Nr", "dates": "Dzień urodzenia / chrztu", "baptism": "Kiedy, gdzie, przez kogo ochrzczony", "parents": "Rodzice, stan; kiedy i gdzie urodzony", "godparents": "Rodzice chrzestni i obecni", "sign": "Podpisy świadków"},
    clothType: { skara: 'chusta wełniana', lovatiesė: 'narzuta' },
    clothH: 'Tkanina i wstążka',
    cloth1: 'Okładka i wstążka to prawdziwe żmudzkie tkaniny ze zbiorów Litewskiego Muzeum Narodowego. Fotografie muzeum wykorzystano na licencji CC BY 4.0.',
    ph: 'Nazwisko, wieś lub data, lata 1886–1890', chooseH: 'Wybierz wpis', chooseP: 'Wskaż wiersz księgi, aby go przeczytać. Kliknij, aby pozostał otwarty.',
    everyH: 'Cała strona w tłumaczeniu', everyP: 'Zatrzymaj wskaźnik na karcie, aby zobaczyć pismo pod nią, albo wybierz wpis, aby zobaczyć uwagi.',
    bapt: 'Chrzest', born: 'ur.', marks: 'Wstążka zaznacza ten wpis.', move: 'Przenieś wstążkę tutaj', from: 'Odczytano z: ',
    key: '<span class="u">Kropkowana linia</span> oznacza odczyt, którego maszyna nie była pewna; <span class="ed">[kursywa w nawiasach]</span> to jej uwagi. Zatrzymaj wskaźnik na nazwisku, aby zobaczyć rosyjski zapis, z którego je odczytano.',
    warn: 'Odczytane i przetłumaczone maszynowo; nikt tego nie sprawdzał. Ufaj rękopisowi bardziej niż tłumaczeniu.',
    sources: 'Źródła', register: 'Księga: parafia rzymskokatolicka w Płungianach, metryki urodzeń i chrztów 1886–1890, Litewskie Państwowe Archiwum Historyczne, 1827/1/23, z <a href="https://www.epaveldas.lt/">epaveldas.lt</a> (do użytku niekomercyjnego).',
    museum: 'Litewskie Muzeum Narodowe', showR: 'Pokaż prawą stronę', showL: 'Pokaż lewą stronę',
    none: 'Nic podobnego nie znaleziono. Spróbuj mniej liter; pisownia w księdze bardzo się waha.', noName: 'imienia nie odczytano', noDate: 'daty nie odczytano',
    found: n => n === 1 ? '1 wpis' : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14)) ? `${n} wpisy` : `${n} wpisów`, more: n => `Pokazano pierwsze ${n}.`, away: 'Wyszarzone wpisy są na stronach, których jeszcze nie ma w tej próbce.',
    tips: 'Wpisz nazwisko w dowolnej pisowni, wieś albo datę, np. „10 stycznia 1888”, „03.1887” lub „#8”.',
    no: 'nr', scan: 'skan', onDate: 'chrzest lub urodzenie', anyText: 'pasujące do', entryNo: 'numer wpisu', and: 'i',
    cloth: { plunge: 'Tkanina okładki: wełniano-lniana narzuta (divonas), koniec XIX w., wieś Palūščiai, rejon płungiański', kretinga: 'Tkanina okładki: pasiasta chusta wełniana, druga połowa XIX w., wieś Budriai, rejon kretyngański', telsiai: 'Tkanina okładki: narzuta tkana techniką gobelinową (divonas), koniec XIX w., wieś Vaštakiai, rejon telszański' },
    ribbon: { mazeikiai: 'Wstążka: pleciona krajka wełniana, 1930, wieś Meinoriai, rejon możejski', taurage: 'Wstążka: okrągło pleciona krajka wełniana, koniec XIX w., rejon taurogski', ukrinai: 'Wstążka: pleciona wełniana krajka-podwiązka, około 1940, wieś Ukrinai, rejon możejski' } },
  ru: { title: 'Žemaičių metrikai', sub: 'Приходские книги Жемайтии. Плунге, крещения, январь 1888 года',
    namesH: "Имена и фамилии", names1: "Имя здесь может встречаться в трёх видах: русскими буквами, которые машина прочла на странице, в передаче на язык, на котором вы читаете, и на полях – как фамилия семьи, записанная писарем второй раз. Это прочтения и передачи, а не отождествления. Две записи с одной фамилией ещё не означают одного человека, а поиск находит похожие написания, не утверждая, что это одна семья.", dataLine: "Прочтения, переводы и модель распознавания открыты: <a href=\"https://github.com/brezgis/samogitia-records\">данные и код</a>, <a href=\"https://huggingface.co/brezgis/samogitia-plunge-htr\">модель</a>.",
    aboutH: 'Об этих книгах',
    about1: 'От крещения до погребения жизнь католика в Жемайтии записывалась в приходские книги. Каждый приход вёл метрические книги о крещениях, браках и смертях. Перед вами одна из них: книга о крещениях Плунгянского прихода Жемайтской епархии за 1886–1890 годы.',
    about2: 'В 1888 году Плунге входило в Российскую империю, в Тельшевский уезд Ковенской губернии, и метрики полагалось вести по-русски. Поэтому священник вписывал литовские и польские имена русскими буквами в печатный русский бланк, а даты ставил по старому юлианскому календарю, который отстаёт от нынешнего на двенадцать дней.',
    readH: 'Как читать запись',
    read1: 'Каждая запись повторяет одну формулу в трёх графах: когда, где и кем крещён младенец; кто его родители, какого они сословия и волости, когда и где он родился; кто были восприемники. Фамилии стоят так, как требует формула, в родительном падеже множественного числа, поэтому здесь они часто оканчиваются на «-овъ», хотя сама семья сказала бы «-ис», «-ас» или «-ус».',
    read2: "Рукопись прочитана моделью распознавания, обученной примерно на 2 300 строках этих книг, каждую из которых независимо прочли и сверили два ИИ-читателя; перевод сделан машиной. Человек результат не проверял. Обычные слова читаются хорошо, имена и деревни часто с ошибками.",
    colsH: "Печатные графы", cols: [["Прозваніе крещаемыхъ", "Фамилия крещаемого, вписана поперёк на полях"], ["№", "Номер записи"], ["Число рожденія / крещенія", "День рождения / день крещения"], ["Когда, гдѣ, кто и кѣмъ … окрещенъ?", "Когда, где, кто и кем крещён, одною ли водою или со всеми обрядами"], ["Какихъ родителей …?", "Каких родителей, какого сословия или общества; когда и где родился"], ["Кто были … воспріемниками …?", "Кто по имени и фамилии были восприемниками и кто присутствовал"], ["Рукоприкладство свидѣтелей …", "Подписи свидетелей записи, по желанию"]],
    sideMargin: "На полях", sideDiffer: x => `В тексте записи машина прочла фамилию как «${x}»; чтение на полях надёжнее.`, sideNo: "№", sideBorn: "родился", sideBapt: "крещён", sideNote: "Позднейшая запись", sexM: "мальчик", sexF: "девочка", sideBy: "Боковые графы прочитаны машиной один раз.",
    heads: {"margin": "Прозваніе крещаемыхъ", "no": "№", "dates": "Число рожденія / крещенія", "baptism": "Когда, гдѣ, кто и кѣмъ окрещенъ", "parents": "Какихъ родителей …", "godparents": "Кто были воспріемниками …", "sign": "Рукоприкладство свидѣтелей"},
    clothType: { skara: 'шерстяной платок', lovatiesė: 'покрывало' },
    clothH: 'Ткань и закладка',
    cloth1: 'Переплёт и закладка — настоящие жемайтские ткани из собрания Национального музея Литвы. Фотографии музея используются по лицензии CC BY 4.0.',
    
    ph: 'Имя, деревня или дата, 1886–1890', chooseH: 'Выберите запись', chooseP: 'Наведите указатель на строку книги, чтобы прочитать её. Щёлкните, чтобы оставить открытой.',
    everyH: 'Вся страница в расшифровке', everyP: 'Наведите указатель на листок, чтобы увидеть рукопись под ним, или выберите запись.',
    bapt: 'Крещение', born: 'рождение', marks: 'Закладка отмечает эту запись.', move: 'Перенести закладку сюда', from: 'Прочитано из: ',
    key: 'Здесь показана машинная расшифровка рукописи в старой орфографии, со всеми её ошибками. Справа от неё — английский перевод.',
    warn: 'Прочитано и переведено машиной; никто не проверял. Доверяйте рукописи, а не расшифровке.',
    sources: 'Источники', register: 'Метрическая книга: Плунгянский римско-католический приход, записи о рождении и крещении за 1886–1890 гг., Литовский государственный исторический архив, 1827/1/23, с сайта <a href="https://www.epaveldas.lt/">epaveldas.lt</a> (некоммерческое использование).',
    museum: 'Национальный музей Литвы', showR: 'Показать правую страницу', showL: 'Показать левую страницу',
    none: 'Ничего похожего не найдено. Попробуйте меньше букв: написание в книге сильно разнится.', noName: 'имя не прочитано', noDate: 'дата не прочитана',
    found: n => `Записей: ${n}`, more: n => `Показаны первые ${n}.`, away: 'Серые записи находятся на страницах, которых пока нет в этом образце.',
    tips: 'Введите имя в любом написании, деревню или дату, например «10 января 1888», «03.1887» или «#8».',
    no: '№', scan: 'скан', onDate: 'крещение или рождение', anyText: 'совпадает с', entryNo: 'номер записи', and: 'и',
    cloth: { plunge: 'Ткань переплёта: покрывало из шерсти и льна (дивонас), конец XIX в., дер. Палушчяй, Плунгеский район', kretinga: 'Ткань переплёта: полосатый шерстяной платок, вторая половина XIX в., дер. Будряй, Кретингский район', telsiai: 'Ткань переплёта: покрывало ковровой техники (дивонас), конец XIX в., дер. Ваштакяй, Тельшяйский район' },
    ribbon: { mazeikiai: 'Закладка: плетёный шерстяной пояс, 1930 г., дер. Мейноряй, Мажейкский район', taurage: 'Закладка: шерстяной пояс круглого плетения, конец XIX в., Таурагский район', ukrinai: 'Закладка: плетёный шерстяной пояс-подвязка, около 1940 г., дер. Укринай, Мажейкский район' } },
};
const X = {
  en: { sub: w => `Parish registers of Samogitia. Plungė, baptisms, ${w}`, front: 'pages without entries', to: ' to ',
    untranslated: 'Not translated yet, so this is the machine’s Russian reading.', ltMissing: '', where: (a, b) => `Scan ${a} of ${b}`,
    prev: 'Turn back a page', next: 'Turn to the next page', nothing: 'No entries were found on these two pages.' },
  lt: { sub: w => `Žemaitijos parapijų knygos. Plungė, krikštai, ${w}`, front: 'puslapiai be įrašų', to: ' – ',
    untranslated: 'Dar neišversta, todėl rodomas mašinos perskaitytas rusiškas tekstas.', ltMissing: 'Lietuviško vertimo dar nėra, rodomas angliškas.', where: (a, b) => `${a} skenas iš ${b}`,
    prev: 'Atversti ankstesnį puslapį', next: 'Versti kitą puslapį', nothing: 'Šiuose dviejuose puslapiuose įrašų nerasta.' },
  pl: { sub: w => `Księgi parafialne Żmudzi. Płungiany, chrzty, ${w}`, front: 'strony bez wpisów', to: ' – ',
    untranslated: 'Jeszcze nie przetłumaczono, więc to rosyjski odczyt maszyny.', ltMissing: 'Polskiego tłumaczenia jeszcze nie ma, pokazano angielskie.', where: (a, b) => `Skan ${a} z ${b}`,
    prev: 'Przewróć stronę wstecz', next: 'Przewróć na następną stronę', nothing: 'Na tych dwóch stronach nie znaleziono wpisów.' },
  ru: { sub: w => `Приходские книги Жемайтии. Плунге, крещения, ${w}`, front: 'страницы без записей', to: ' – ',
    untranslated: '', ltMissing: '', where: (a, b) => `Скан ${a} из ${b}`,
    prev: 'Перелистнуть назад', next: 'Перелистнуть вперёд', nothing: 'На этих двух страницах записей не найдено.' },
};
for (const k in X) Object.assign(T[k], X[k]);
/* strings that name the parish, the years or the archive file */
const EPAV = '<a href="https://www.epaveldas.lt/">epaveldas.lt</a>';
const BOOKTEXT = (N => ({
  en: { sub: w => `${N.en.name}, baptisms, ${w}`,
    about1: `From baptism to burial, a Catholic life in Samogitia was written into the parish books. Every parish kept registers, metrikai in Lithuanian, of baptisms, marriages and deaths. This is one of them: the baptisms of ${N.en.name} parish, in the diocese of Samogitia, for ${Y0} to ${Y1}.`,
    about2: `In these years ${N.en.name} lay in the Russian Empire, in ${N.en.county} county of Kovno governorate, and the registers had to be kept in Russian. So the priest wrote Lithuanian and Polish names in Russian letters, into a printed Russian form, and dated them by the old Julian calendar, ${LATE ? 'twelve days behind the one we use, thirteen from March 1900' : 'twelve days behind the one we use'}.`,
    ph: `Name, village or date, ${Y0} to ${Y1}`,
    register: `Roman Catholic parish of ${N.en.name}, births and baptisms ${Y0}–${Y1}. Lithuanian State Historical Archives, ${BK.archive}, from ${EPAV}; the scans are for non-commercial use.`,
    tips: `Try a name in any spelling, a village, or a date such as “10 January ${YMID}”, “03.${YMID}” or “#8”.` },
  lt: { sub: w => `${N.lt.name}, krikštai, ${w}`,
    about1: `Nuo krikšto iki laidotuvių Žemaitijos kataliko gyvenimas buvo užrašomas parapijos knygose. Kiekviena parapija vedė krikšto, santuokos ir mirties metrikus. Čia viena tokių knygų: Žemaičių vyskupijos ${N.lt.gen} parapijos krikšto metrikai, ${Y0}–${Y1} m.`,
    about2: `Šiais metais ${N.lt.name} priklausė Rusijos imperijai, Kauno gubernijos ${N.lt.countyGen} apskričiai, ir metrikus reikėjo rašyti rusiškai. Todėl kunigas lietuviškus ir lenkiškus vardus rašė rusiškomis raidėmis į spausdintą rusišką formą, o datas žymėjo pagal senąjį Julijaus kalendorių, ${LATE ? 'dvylika, o nuo 1900 m. kovo trylika dienų' : 'dvylika dienų'} atsiliekantį nuo dabartinio.`,
    ph: `Vardas, kaimas arba data, ${Y0}–${Y1} m.`,
    register: `${N.lt.gen} Romos katalikų parapijos gimimo ir krikšto metrikai, ${Y0}–${Y1} m. Lietuvos valstybės istorijos archyvas, ${BK.archive}, iš ${EPAV}; skenai skirti nekomerciniam naudojimui.`,
    tips: `Rašykite vardą bet kokia rašyba, kaimą arba datą, pvz., „${YMID} sausio 10“, „03.${YMID}“ ar „#8“.` },
  pl: { sub: w => `${N.pl.name}, chrzty, ${w}`,
    about1: `Od chrztu po pogrzeb życie katolika na Żmudzi zapisywano w księgach parafialnych. Każda parafia prowadziła metryki chrztów, ślubów i zgonów. To jedna z nich: metryki chrztów parafii ${N.pl.name} w diecezji żmudzkiej za lata ${Y0}–${Y1}.`,
    about2: `W tych latach ${N.pl.name} ${N.pl.lay} w Cesarstwie Rosyjskim, w powiecie ${N.pl.countyLoc} guberni kowieńskiej, a metryki należało prowadzić po rosyjsku. Ksiądz zapisywał więc litewskie i polskie imiona i nazwiska rosyjskimi literami w drukowanym rosyjskim formularzu i datował je według dawnego kalendarza juliańskiego, o ${LATE ? 'dwanaście, a od marca 1900 roku o trzynaście dni' : 'dwanaście dni'} wcześniejszego od dzisiejszego.`,
    ph: `Nazwisko, wieś lub data, lata ${Y0}–${Y1}`,
    register: `Parafia rzymskokatolicka w ${N.pl.loc}, metryki urodzeń i chrztów ${Y0}–${Y1}. Litewskie Państwowe Archiwum Historyczne, ${BK.archive}, z ${EPAV}; skany do użytku niekomercyjnego.`,
    tips: `Wpisz nazwisko w dowolnej pisowni, wieś albo datę, np. „10 stycznia ${YMID}”, „03.${YMID}” lub „#8”.` },
  ru: { sub: w => `${N.ru.name}, крещения, ${w}`,
    about1: `От крещения до погребения жизнь католика в Жемайтии записывалась в приходские книги. Каждый приход вёл метрические книги о крещениях, браках и смертях. Перед вами одна из них: книга о крещениях ${N.ru.adjGen} прихода Жемайтской епархии за ${Y0}–${Y1} годы.`,
    about2: `В эти годы ${N.ru.name} ${N.ru.was} в Российскую империю, в ${N.ru.county} уезд Ковенской губернии, и метрики полагалось вести по-русски. Поэтому священник вписывал литовские и польские имена русскими буквами в печатный русский бланк, а даты ставил по старому юлианскому календарю, который отстаёт от нынешнего на ${LATE ? 'двенадцать, а с марта 1900 года на тринадцать дней' : 'двенадцать дней'}.`,
    ph: `Имя, деревня или дата, ${Y0}–${Y1}`,
    register: `${N.ru.adjNom} римско-католический приход, записи о рождении и крещении за ${Y0}–${Y1} гг. Литовский государственный исторический архив, ${BK.archive}, с сайта ${EPAV}; сканы только для некоммерческого использования.`,
    tips: `Введите имя в любом написании, деревню или дату, например «10 января ${YMID}», «03.${YMID}» или «#8».` },
}))(PARISH.names);
for (const k in BOOKTEXT) Object.assign(T[k], BOOKTEXT[k]);
const LIMIS = { plunge: '1056757085', kretinga: '1059250648', telsiai: '1057411152', mazeikiai: '914006288', taurage: '914017553', ukrinai: '914014451' };
const store = { get: k => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} } };
let lang = 'en';
const t = () => T[lang];
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const pad = n => String(n).padStart(4, '0');
const reduced = () => matchMedia('(prefers-reduced-motion:reduce)').matches;
function showDate(d, noYear) {
  if (!d) return '';
  const [y, m, dd] = d.split('-').map(Number);
  const opt = { month: 'long' }; if (dd) opt.day = 'numeric'; if (!noYear) opt.year = 'numeric';
  return new Intl.DateTimeFormat(LOCALE[lang], { ...opt, timeZone: 'UTC' }).format(new Date(Date.UTC(y, m - 1, dd || 1))).replace(/\.$/, '');
}

/* the open spread */
let S = null, pages = {}, byRow = {}, slip = null;
let pinned = null, hovered = null;
let marked = (() => { try { return JSON.parse(store.get('ribbon')) || null; } catch { return null; } })() || { row: BK.row || '', scan: BK.scan };
const params = new URLSearchParams(location.hash.slice(1));
const cache = {};
const loadSpread = scan => cache[scan] || (cache[scan] = fetch(`spreads/${pad(scan)}.json`).then(r => r.json()));
const preload = src => new Promise(res => { const i = new Image(); i.onload = i.onerror = res; i.src = src; });
const shown = (e, l = lang) => e.html[l] ? l : e.html.en && l !== 'ru' ? 'en' : 'ru';

function buildPages() {
  block.innerHTML = ''; pages = {}; byRow = {};
  block.style.gridTemplateColumns = `${S.pages.L.w}fr ${S.pages.R.w}fr`;
  for (const side of ['L', 'R']) {
    const p = el('div', 'page'); p.dataset.side = side; p.style.aspectRatio = `${S.pages[side].w} / ${S.pages[side].h}`;
    const img = el('img'), src = S.pages[side].img;
    // a page image that fails to arrive is asked for again (three times) instead of leaving its caption
    img.onerror = () => { const n = +(img.dataset.retry || 0); if (n < 3) { img.dataset.retry = n + 1; setTimeout(() => { img.src = `${src}?retry=${n + 1}`; }, 500 * (n + 1)); } };
    img.src = src; img.alt = side === 'L' ? 'Left-hand page of the register' : 'Right-hand page of the register'; img.draggable = false;
    p.append(img, el('div', 'tint'), el('div', 'fold'));
    pages[side] = p; block.append(p);
  }
  for (const e of S.entries) {
    byRow[e.row] = e;
    const p = pages[e.side], b = el('button', 'band');
    b.type = 'button'; b.dataset.row = e.row; b.setAttribute('aria-pressed', 'false');
    b.style.top = e.band[0] + '%'; b.style.height = (e.band[1] - e.band[0]) + '%';
    p.append(b);
    if (e.band2 && pages[e.band2.side]) {          // two-page form: the entry continues on the facing page
      const b2 = b.cloneNode(false);
      b2.style.top = e.band2.band[0] + '%'; b2.style.height = (e.band2.band[1] - e.band2.band[0]) + '%';
      pages[e.band2.side].append(b2);
    }
    const boxesFor = Object.assign({}, e.cells, e.sideBox ? { side: e.sideBox } : {});
    for (const c of Object.keys(boxesFor)) {
      const l = el('div', 'leaf' + (c === 'side' ? ' side' : '')); l.dataset.row = e.row; l.dataset.cell = c;
      const [x0, y0, x1, y1] = boxesFor[c];
      l.style.left = x0 + '%'; l.style.top = y0 + '%'; l.style.width = (x1 - x0) + '%'; l.style.minHeight = (y1 - y0) + '%';
      (pages[e.cellSide && e.cellSide[c]] || p).append(l);
    }
  }
  for (const side of ['L', 'R']) {               // translated printed column headings at the top of the page
    const hs = (S.heads && S.heads[side]) || [];
    if (!hs.length) continue;
    // the translated header shows only while the pointer is over the printed header (tap toggles on touch)
    const zone = el('div', 'headzone');
    const top = Math.min(...hs.map(h => h[3])), bot = Math.max(...hs.map(h => h[4]));
    zone.style.top = top + '%'; zone.style.height = (bot - top) + '%';
    const heads = [];
    for (const [k, x0, x1, y0, y1] of hs) {
      const l = el('div', 'leaf head' + (x1 - x0 < 7 ? ' narrow' : '')); l.dataset.head = k;
      l.style.left = x0 + '%'; l.style.top = y0 + '%'; l.style.width = (x1 - x0) + '%'; l.style.height = (y1 - y0) + '%';
      pages[side].append(l); heads.push(l);
    }
    const show = on => heads.forEach(l => l.classList.toggle('on', on));
    zone.addEventListener('mouseenter', () => show(true));
    zone.addEventListener('mouseleave', () => show(false));
    zone.addEventListener('click', () => show(!heads[0].classList.contains('on')));
    pages[side].append(zone);
  }
  slip = el('div', 'slip'); block.append(slip);
  fillLeaves();
}
function fillLeaves() {
  block.querySelectorAll('.leaf[data-row]').forEach(l => { const e = byRow[l.dataset.row], s = shown(e), h = e.html[s];
    l.lang = s; l.innerHTML = (h && h[l.dataset.cell]) || (e.html.ru[l.dataset.cell] || ''); });
  block.querySelectorAll('.leaf.head').forEach(l => { l.lang = lang; l.textContent = t().heads[l.dataset.head] || ''; });
  block.querySelectorAll('[data-draft]').forEach(s => s.title = t().from + s.dataset.draft);
  block.querySelectorAll('.band').forEach(b => b.setAttribute('aria-label', plain(fullName(byRow[b.dataset.row]))));
}
const fullName = e => lang === 'ru' || !e.child ? esc([e.childRu, e.surnameRu].filter(Boolean).join(' ') || t().noName)
  : esc(lang === 'pl' && e.childPl || e.child) + (e.surname ? ` <span class="${e.surnameQ ? 'u' : ''}">${esc(lang === 'lt' && e.surnameLt || lang === 'pl' && e.surnamePl || e.surname)}</span>` : '');
const plain = h => h.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const current = () => hovered || pinned;

function sideHtml(e) {           // printed columns 1-3: margin surname, No., sex, days, later notes
  const c = e.sideCols, L = t();
  if (!c) return '';
  // the margin and the parents column write the same surname twice; the heading carries the
  // reconciled form, so the margin is quoted as written and a second form only when they differ
  const rend = e.surnameSrc ? '' : lang === 'lt' ? c.margin_lt : lang === 'en' ? c.margin_en : '';
  const differ = e.surnameAlt && lang !== 'ru' ? ` <span class="ed">${L.sideDiffer(esc(e.surnameAlt))}</span>` : '';
  const sex = c.sex === 'M' ? L.sexM : c.sex === 'F' ? L.sexF : '';
  const bits = [c.entry_no && `${L.sideNo} ${esc(c.entry_no)}`, sex, c.birth_day && `${L.sideBorn} ${esc(c.birth_day)}`,
    c.baptism_day && `${L.sideBapt} ${esc(c.baptism_day)}`].filter(Boolean);
  const margin = c.margin_surname ? `${L.sideMargin}: <span lang="ru">${esc(c.margin_surname)}</span>${rend ? ` (${esc(rend)})` : ''}${differ}` : '';
  const noteT = lang === 'lt' ? c.notes_lt : lang === 'en' || lang === 'pl' ? c.notes_en : c.notes_ru;
  const note = c.notes_ru ? `<p class="side-note">${L.sideNote}: ${esc(noteT || c.notes_ru)}</p>` : '';
  return `<p class="side">${[margin, bits.join(', ')].filter(Boolean).join(' · ')}</p>${note}`;
}
function render() {
  if (!S) return;
  const mode = body.dataset.read, cur = current(), L = t();
  book.classList.toggle('has-pick', !!cur);
  block.querySelectorAll('.leaf[data-row]').forEach(l => l.classList.toggle('on', mode === 'every' ? true : mode === 'one' ? l.dataset.row === cur : false));
  block.querySelectorAll('.band').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.row === pinned)));
  const e = byRow[cur];
  slip.classList.toggle('on', !!e);
  const cap = $('#cap'), other = $('#ru');
  if (e) {
    const s = shown(e), h = e.html[s], issues = e.issues[lang] || (lang !== 'ru' && e.issues.en) || '';
    const when = [e.date && `${L.bapt}: ${showDate(e.date)}`, e.born && `${L.born} ${showDate(e.born)}`].filter(Boolean).join(', ');
    const note = s === lang ? '' : s === 'en' ? L.ltMissing : L.untranslated;
    const title = `${e.n ? e.n + '. ' : ''}${fullName(e)}`;
    slip.innerHTML = `<h2>${title}</h2><p class="when">${when}</p><p>${h.baptism}</p><p>${h.parents}</p><p>${h.godparents}</p>${sideHtml(e)}
      <dl>${e.names.map(([ru, en]) => `<dt lang="ru">${esc(ru.trim())}</dt><dd>${esc(en.trim())}</dd>`).join('')}</dl><p class="note">${esc(issues)}</p>`;
    slip.style.left = ((e.side === 'R' ? 0 : 50) + 3) + '%';
    slip.style.top = Math.max(3, Math.min(e.band[0] - 6, 38)) + '%';
    const here = marked.row === e.row;
    cap.innerHTML = `<h2>${title}</h2><p>${[when, esc(issues)].filter(Boolean).join('. ')}</p>${note ? `<p>${note}</p>` : ''}
      ${here ? `<p>${L.marks}</p>` : `<button type="button" id="mark">${L.move}</button>`}`;
    const side = s === 'ru' ? (e.html.en ? 'en' : null) : 'ru';   // the desk shows the other side of the translation
    other.lang = side || 'ru';
    other.textContent = side ? ['baptism', 'parents', 'godparents'].map(c => plain(e.html[side][c])).join(' ') : '';
    const m = $('#mark'); if (m) m.onclick = () => { marked = { row: e.row, scan: S.scan }; store.set('ribbon', JSON.stringify(marked)); render(); };
  } else {
    other.textContent = '';
    cap.innerHTML = !S.entries.length ? `<h2>${L.where(S.scan, SPREADS.length)}</h2><p>${L.nothing}</p>`
      : mode === 'every' ? `<h2>${L.everyH}</h2><p>${L.everyP}</p>` : `<h2>${L.chooseH}</h2><p>${L.chooseP}</p>`;
  }
  $('.ribbon').classList.toggle('tucked', marked.scan !== S.scan);
}
function chrome() {            // everything around the pages that depends on which spread is open
  const L = t(), i = SPREADS.findIndex(m => m.scan === S.scan), m = SPREADS[i];
  const ds = S.entries.filter(e => e.date && e.y === m.y && +e.date.slice(0, 4) === m.y).map(e => e.date.slice(0, 7)).sort();
  let when = m.y ? String(m.y) : L.front;
  if (ds.length) {
    const a = ds[0], b = ds[ds.length - 1];
    when = a === b ? showDate(a) : showDate(a, true) + L.to + showDate(b);
  }
  $('#sub').textContent = L.sub(when);
  $('#where').textContent = L.where(S.scan, SPREADS.length);
  $('#scrub').value = i + 1;
  $('#prev').disabled = i === 0; $('#next').disabled = i === SPREADS.length - 1;
  $('#prev').setAttribute('aria-label', L.prev); $('#next').setAttribute('aria-label', L.next);
  $('#edgeL').setAttribute('aria-label', L.prev); $('#edgeR').setAttribute('aria-label', L.next);
  document.querySelectorAll('.years button').forEach(b => b.setAttribute('aria-current', String(+b.dataset.y === m.y)));
  params.set('s', S.scan); pinned ? params.set('pick', pinned) : params.delete('pick'); params.set('lang', lang);
  history.replaceState(null, '', '#' + params);
}

/* turning pages */
let turning = false;
/* Page images got ready ahead of a turn: fetched and decoded, and kept (a few) so the leaf can
   move the moment it is asked to. */
const readied = new Map();
function ready(src) {
  if (!readied.has(src)) {
    const im = new Image(); im.src = src;
    readied.set(src, (im.decode ? im.decode() : new Promise(res => { im.onload = im.onerror = res; })).then(() => im, () => im));
    if (readied.size > 12) readied.delete(readied.keys().next().value);
  }
  return readied.get(src);
}

/* The turning leaf. A sheet of paper bends: it is cut into narrow vertical strips, each hinged on
   the one before it, so the free edge can lift ahead of the rest and settle after it. The first
   strip is hinged at the spine and carries the turn; the others only add the bend. Each strip
   shows its slice of the outgoing page on the front and of the incoming page on the back. */
const STRIPS = 8, TURN_MS = 820;
const FREEZE = params.has('turn') ? Math.max(0, Math.min(1, +params.get('turn'))) : null;   // #turn=0.4 holds a demonstration turn at 40%, to look at it
function buildLeaf(old, next, dir) {
  const stay = dir > 0 ? 'L' : 'R', turn = dir > 0 ? 'R' : 'L', fwd = dir > 0;
  const hold = el('div', 'hold'), o = old[stay];
  Object.assign(hold.style, { left: o.left + 'px', width: o.width + 'px', height: o.height + 'px', backgroundImage: `url("${o.src}")` });
  const flip = el('div', 'flip ' + (fwd ? 'fwd' : 'back')), tp = old[turn];
  Object.assign(flip.style, { left: tp.left + 'px', width: tp.width + 'px', height: tp.height + 'px' });
  const cast = el('div', 'cast ' + (fwd ? 'fwd' : 'back'));
  const segs = [];
  let parent = flip;
  for (let k = 0; k < STRIPS; k++) {
    const seg = el('div', 'seg'), front = el('div', 'f front'), rear = el('div', 'f rear');
    const fromLeft = k / (STRIPS - 1) * 100, fromRight = (STRIPS - 1 - k) / (STRIPS - 1) * 100;
    front.style.backgroundImage = `url("${tp.src}")`; front.style.backgroundPositionX = (fwd ? fromLeft : fromRight) + '%';
    rear.style.backgroundImage = `url("${next.pages[stay].img}")`; rear.style.backgroundPositionX = (fwd ? fromRight : fromLeft) + '%';
    front.append(el('div', 'shade')); rear.append(el('div', 'shade'));
    seg.append(front, rear); parent.append(seg); segs.push(seg); parent = seg;
  }
  return { nodes: [hold, cast, flip], segs, cast };
}
async function turnLeaf(leaf, dir) {
  await new Promise(res => { requestAnimationFrame(res); setTimeout(res, 80); });       // one frame for the rebuilt spread under the leaf
  const s = dir > 0 ? -1 : 1, opt = { duration: TURN_MS, fill: 'forwards' }, anims = [];
  const rot = a => `rotateY(${(s * a).toFixed(2)}deg)`;
  // the spine strip carries the whole turn, slow to leave and slow to land
  anims.push(leaf.segs[0].animate([{ transform: rot(0) }, { transform: rot(180) }], { ...opt, easing: 'cubic-bezier(.42,0,.26,1)' }));
  // every further strip bends on the one before: ahead of it while the page lifts, behind it while it falls
  leaf.segs.slice(1).forEach((seg, k) => {
    const lead = 4.2 + k * .9, lag = 3.4 + k * .75;
    anims.push(seg.animate([
      { transform: rot(0), easing: 'cubic-bezier(.3,0,.4,1)' },
      { transform: rot(lead), offset: .2, easing: 'cubic-bezier(.4,0,.6,1)' },
      { transform: rot(-lag), offset: .68, easing: 'cubic-bezier(.3,0,.3,1)' },
      { transform: rot(0) }], opt));
  });
  // light: the outgoing side darkens as it turns from the lamp, the incoming side clears as it comes down
  leaf.segs.forEach((seg, k) => {
    // in the air the sheet lets the page under it show through, more toward its free edge
    const thin = 1 - .3 * (k / (STRIPS - 1)) ** 1.6;
    for (const f of seg.querySelectorAll(':scope > .f')) anims.push(f.animate([{ opacity: 1 }, { opacity: thin, offset: .22 }, { opacity: thin, offset: .78 }, { opacity: 1 }], opt));
    anims.push(seg.querySelector('.front .shade').animate([{ opacity: 0 }, { opacity: .34, offset: .5 }, { opacity: .34 }], opt));
    anims.push(seg.querySelector('.rear .shade').animate([{ opacity: .3 }, { opacity: .3, offset: .5 }, { opacity: 0 }], opt));
  });
  anims.push(leaf.cast.animate([{ opacity: 0 }, { opacity: 1, offset: .45 }, { opacity: 0 }], { ...opt, easing: 'ease-in-out' }));
  if (FREEZE != null) { anims.forEach(a => { a.pause(); a.currentTime = TURN_MS * FREEZE; }); await new Promise(() => {}); }
  await Promise.race([anims[0].finished.catch(() => {}), new Promise(res => setTimeout(res, TURN_MS + 500))]);
}
async function go(scan, row, quiet) {
  if (turning) return;
  const i = Math.max(0, Math.min(SPREADS.length - 1, SPREADS.findIndex(m => m.scan === scan)));
  scan = SPREADS[i].scan;
  if (S && S.scan === scan) { if (row && byRow[row]) pick(row, true); return; }
  turning = true;
  const next = await loadSpread(scan);
  if (S) await Promise.race([Promise.all([ready(next.pages.L.img), ready(next.pages.R.img)]), new Promise(res => setTimeout(res, 900))]);   // instant when the neighbour was got ready; the first spread is laid out at once and its scans fill in
  const dir = S ? Math.sign(scan - S.scan) : 0;
  const old = dir && !quiet && !reduced() && pages.L && getComputedStyle(pages.R).display !== 'none' && getComputedStyle(pages.L).display !== 'none'
    ? Object.fromEntries(['L', 'R'].map(s => [s, { src: S.pages[s].img, left: pages[s].offsetLeft, width: pages[s].offsetWidth, height: pages[s].offsetHeight }])) : null;
  let leaf;
  if (old) leaf = buildLeaf(old, next, dir);        // made from the outgoing spread's measurements, before the rebuild
  S = next; pinned = row && S.entries.some(e => e.row === row) ? row : null; hovered = null;
  buildPages(); render(); chrome();
  if (leaf) {
    block.append(...leaf.nodes);                    // same task as the rebuild: the new spread never shows early
    await turnLeaf(leaf, dir);
    leaf.nodes.forEach(n => n.remove());
  }
  turning = false;
  if (pinned) pick(pinned, true);
  for (const d of [1, -1]) { const m = SPREADS[i + d]; if (m) loadSpread(m.scan).then(n => { ready(n.pages.L.img); ready(n.pages.R.img); }); }
}
const step = d => { const i = SPREADS.findIndex(m => m.scan === S.scan) + d; if (SPREADS[i]) go(SPREADS[i].scan); };
function pick(row, focus) {
  pinned = row; hovered = null;
  book.dataset.show = byRow[row].side; syncTurn(); render(); chrome();
  const b = block.querySelector(`.band[data-row="${row}"]`); if (focus) b.focus({ preventScroll: true });
  b.scrollIntoView({ block: 'center', behavior: reduced() ? 'auto' : 'smooth' });
}
block.addEventListener('pointerover', ev => { const b = ev.target.closest('.band'); if (b && ev.pointerType === 'mouse') { hovered = b.dataset.row; render(); } });
block.addEventListener('pointerleave', () => { hovered = null; render(); });
block.addEventListener('click', ev => { const b = ev.target.closest('.band'); if (!b) return; pinned = pinned === b.dataset.row ? null : b.dataset.row; hovered = null; render(); chrome(); });
document.addEventListener('keydown', ev => {
  const a = document.activeElement, typing = a && /INPUT|TEXTAREA/.test(a.tagName);
  if (ev.key === 'Escape') { pinned = hovered = null; closeHits(); render(); chrome(); }
  if (!typing && ev.key === 'ArrowRight') step(1);
  if (!typing && ev.key === 'ArrowLeft') step(-1);
  if ((ev.key === 'ArrowDown' || ev.key === 'ArrowUp') && a.classList.contains('band')) {
    const rows = S.entries.map(e => e.row), i = rows.indexOf(a.dataset.row) + (ev.key === 'ArrowDown' ? 1 : -1);
    if (rows[i]) { ev.preventDefault(); pick(rows[i], true); }
  }
});
$('#prev').onclick = $('#edgeL').onclick = () => step(-1);
$('#next').onclick = $('#edgeR').onclick = () => step(1);
$('#scrub').max = SPREADS.length;
$('#scrub').addEventListener('input', ev => $('#where').textContent = t().where(SPREADS[ev.target.value - 1].scan, SPREADS.length));
$('#scrub').addEventListener('change', ev => go(SPREADS[ev.target.value - 1].scan));
/* the same parish's books before and after this one stand at either end of the year row */
const SHELF = PARISH.books.filter(b => b.state === 'open'), HERE = SHELF.findIndex(b => b.dir === BK.dir);
const span = b => b.years[0] === b.years[1] ? `${b.years[0]}` : `${b.years[0]}–${b.years[1]}`;
const bookLink = (b, cls) => { const a = el('a', cls); a.href = `../${b.dir}/`; a.textContent = span(b); return a; };
if (HERE > 0) $('.years').append(bookLink(SHELF[HERE - 1], 'before'));
for (const y of [...new Set(SPREADS.map(m => m.y).filter(Boolean))].sort()) {
  const b = el('button', '', y); b.type = 'button'; b.dataset.y = y;
  b.onclick = () => go(SPREADS.find(m => m.y === y).scan);
  $('.years').append(b);
}
if (HERE >= 0 && SHELF[HERE + 1]) $('.years').append(bookLink(SHELF[HERE + 1], 'after'));
$('#ribbonBtn').onclick = () => go(marked.scan, marked.row).then(() => { if (S.scan === marked.scan && byRow[marked.row]) pick(marked.row, true); });
const turn = $('#turn');
const syncTurn = () => turn.textContent = book.dataset.show === 'R' ? t().showL : t().showR;
turn.onclick = () => { book.dataset.show = book.dataset.show === 'R' ? 'L' : 'R'; syncTurn(); };

/* look (set from the address, e.g. #cloth=kretinga&ribbon=taurage) and language */
const form = $('#tryon'), AXES = ['cloth', 'ribbon', 'read', 'paper', 'room'];
function applyLook() {
  params.forEach((v, k) => { if (form.elements[k]) form.elements[k].value = v; });
  for (const a of AXES) body.dataset[a] = form.elements[a].value || body.dataset[a];
  // each volume has its own cover cloth and ribbon (book.js); the address can still try others on
  if (!params.get('cloth') && BK.cloth) body.dataset.cloth = BK.cloth;
  if (!params.get('ribbon') && BK.ribbon) body.dataset.ribbon = BK.ribbon;
  $('#cover').style.backgroundImage = `url(../textiles/cloth-${body.dataset.cloth}.jpg)`;
  if (body.dataset.ribbon !== 'none') $('#ribbonImg').src = `../textiles/ribbon-${body.dataset.ribbon}.webp`;
  document.documentElement.style.setProperty('--sheer', form.elements.sheer.value / 100);
  document.documentElement.dataset.room = body.dataset.room;
}
function setLang(l) {
  lang = l; store.set('lang', l); document.documentElement.lang = l;
  document.querySelectorAll('input[name=lang]').forEach(r => r.checked = r.value === l);
  const L = t();
  document.title = L.title; $('#title').textContent = L.title;
  $('#q').placeholder = L.ph; $('#q').setAttribute('aria-label', L.ph);
  $('#key').innerHTML = L.key; $('#warn').textContent = L.warn; $('#register').innerHTML = L.register;
  for (const k of ['aboutH', 'about1', 'about2', 'readH', 'read1', 'read2', 'clothH', 'cloth1', 'namesH', 'names1']) $('#' + k).textContent = L[k];
  $('#sourcesH').textContent = L.sources; $('#dataLine').innerHTML = L.dataLine;
  $('#colsH').textContent = L.colsH;
  $('#cols').innerHTML = L.cols.map(([ru, x]) => `<li><span lang="ru">${esc(ru)}</span> — ${esc(x)}</li>`).join('');
  const cl = body.dataset.cloth, meta = (LIB.cloths || {})[cl];       // later cloths are named by their museum number
  const clothCap = L.cloth[cl] || (meta ? `c: ${L.clothType[meta.type] || meta.type}, ${meta.place}` : '');
  const cr = [[clothCap, LIMIS[cl] || (meta && cl)], [L.ribbon[body.dataset.ribbon], LIMIS[body.dataset.ribbon]]].filter(c => c[0]);
  $('#things').innerHTML = cr.map(([txt, id]) => `<figure><img src="../textiles/src/${id}.jpg" alt="" loading="lazy"><figcaption>${txt.replace(/^[^:]+:\s*/, '').replace(/^./, c => c.toUpperCase())}. <a href="https://www.limis.lt/valuables/e/805191/${id}">${L.museum}</a>, CC BY 4.0.</figcaption></figure>`).join('');
  if (S) { fillLeaves(); syncTurn(); render(); chrome(); }
  if ($('#q').value.trim() && !hits.hidden) runSearch();
}
document.querySelectorAll('input[name=lang]').forEach(r => r.addEventListener('change', () => setLang(r.value)));

/* search: every year, one folded spelling across Cyrillic, Polish and Lithuanian forms, plus dates */
const CYR = {а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'e',ж:'z',з:'z',и:'i',і:'i',й:'i',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'h',ц:'c',ч:'c',ш:'s',щ:'s',ъ:'',ы:'i',ь:'',ѣ:'e',э:'e',ю:'iu',я:'ia',ѳ:'f',ѵ:'i'};
const bare = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
const fold = s => bare(s.toLowerCase().replace(/[а-яёіѣѳѵ]/g, c => c in CYR ? CYR[c] : c))
  .replace(/sz|sh|zh|rz/g, 's').replace(/cz|ch|ts/g, 'c').replace(/kh/g, 'h').replace(/w/g, 'v').replace(/[yj]/g, 'i').replace(/ie/g, 'e').replace(/(.)\1+/g, '$1');
const stem = w => w.replace(/(ovnogo|evnogo|ovnoiu|ovna|evna|ovih|skih|skii|skago|ogo|oiu|ov|ev|ih|is|as|us|a|u|i|e)$/, m => w.length - m.length >= 3 ? '' : m);
const term = w => { const f = stem(fold(w)); return f.length > 1 ? f : null; };
const mini = new MiniSearch({
  idField: 'row', fields: ['child', 'parents', 'vil', 'god', 'priest', 'en'],
  extractField: (d, f) => f === 'parents' ? [d.father, d.mother, d.sur].filter(Boolean).join(' ') : (d[f] || ''),
  tokenize: s => s.split(/[^\p{L}\p{N}]+/u).filter(Boolean), processTerm: term,
  searchOptions: { prefix: true, fuzzy: w => w.length > 3 ? .3 : 0, combineWith: 'AND', boost: { child: 2, parents: 2, en: 2, vil: 1.5 }, weights: { fuzzy: .6, prefix: .9 } },
});
mini.addAll(INDEX);
const rec = Object.fromEntries(INDEX.map(r => [r.row, r]));
const MONTHS = [['january','jan','styczen','stycznia','sausis','sausio','январь','января','янв'],['february','feb','luty','lutego','vasaris','vasario','февраль','февраля','фев'],['march','mar','marzec','marca','kovas','kovo','март','марта'],
  ['april','apr','kwiecien','kwietnia','balandis','balandzio','апрель','апреля','апр'],['may','maj','maja','geguze','geguzes','май','мая'],['june','jun','czerwiec','czerwca','birzelis','birzelio','июнь','июня'],['july','jul','lipiec','lipca','liepa','liepos','июль','июля'],
  ['august','aug','sierpien','sierpnia','rugpjutis','rugpjucio','август','августа','авг'],['september','sep','sept','wrzesien','wrzesnia','rugsejis','rugsejo','сентябрь','сентября','сен'],['october','oct','pazdziernik','pazdziernika','spalis','spalio','октябрь','октября','окт'],
  ['november','nov','listopad','listopada','lapkritis','lapkricio','ноябрь','ноября','ноя'],['december','dec','grudzien','grudnia','gruodis','gruodzio','декабрь','декабря','дек']];
const MON = {}; MONTHS.forEach((ws, i) => ws.forEach(w => MON[bare(w)] = i + 1));
function parse(q) {
  const want = { y: null, m: null, d: null, n: null, words: [] };
  for (let tok of q.split(/[\s,]+/).filter(Boolean)) {
    let m;
    const b = bare(tok).replace(/\.$/, '');
    if ((m = b.match(/^(?:#|no\.?|nr\.?|№)(\d{1,3})$/))) want.n = +m[1];
    else if ((m = b.match(/^(1[789]\d\d)-(\d{1,2})(?:-(\d{1,2}))?$/))) { want.y = +m[1]; want.m = +m[2]; if (m[3]) want.d = +m[3]; }
    else if ((m = b.match(/^(\d{1,2})[./](\d{1,2})[./](1[789]\d\d)$/))) { want.d = +m[1]; want.m = +m[2]; want.y = +m[3]; }
    else if ((m = b.match(/^(\d{1,2})[./](1[789]\d\d)$/))) { want.m = +m[1]; want.y = +m[2]; }
    else if (/^\d{4}$/.test(b) && +b >= Y0 - 1 && +b <= Y1) want.y = +b;
    else if (MON[b]) want.m = MON[b];
    else if ((m = b.match(/^(\d{1,2})(?:st|nd|rd|th|d|го|е)?$/)) && +m[1] >= 1 && +m[1] <= 31) want.d = +m[1];
    else if (!/^(m|г|год|года|metu|d|of|the)$/.test(b)) want.words.push(tok);
  }
  if (want.d && !want.m && !want.y && want.n == null) { want.n = want.d; want.d = null; }   // a bare number is an entry number
  return want;
}
const hasDate = w => w.y || w.m || w.d;
const dateFits = (iso, w, regYear) => {
  if (!iso) return !w.m && !w.d && w.y === regYear;
  const [y, m, d] = iso.split('-').map(Number);
  return (!w.y || w.y === y) && (!w.m || w.m === m) && (!w.d || w.d === d);
};
function search(q) {
  const w = parse(q);
  const ok = r => (w.n == null || r.n === w.n) && (!hasDate(w) || dateFits(r.bapt, w, r.y) || (r.born && dateFits(r.born, w, r.y)));
  let rows;
  if (w.words.length) rows = mini.search(w.words.join(' '), { filter: h => ok(rec[h.id]) }).map(h => rec[h.id]);
  else if (hasDate(w) || w.n != null) rows = INDEX.filter(ok).sort((a, b) => (a.bapt || a.y + '-99').localeCompare(b.bapt || b.y + '-99') || (a.n || 0) - (b.n || 0));
  else rows = [];
  return { w, rows };
}
const hits = $('#hits'), LIMIT = 40;
const closeHits = () => { hits.innerHTML = ''; hits.hidden = true; };
function describe(w) {
  const L = t(), parts = [];
  if (hasDate(w)) {
    const opt = {}; if (w.d) opt.day = 'numeric'; if (w.m) opt.month = 'long'; if (w.y) opt.year = 'numeric';
    parts.push(`${L.onDate} ${w.m || w.y ? new Intl.DateTimeFormat(LOCALE[lang], { ...opt, timeZone: 'UTC' }).format(new Date(Date.UTC(w.y || YMID, (w.m || 1) - 1, w.d || 1))) : w.d}`);
  }
  if (w.n != null) parts.push(`${L.entryNo} ${w.n}`);
  if (w.words.length) parts.push(`${L.anyText} “${esc(w.words.join(' '))}”`);
  return parts.join(', ');
}
function runSearch() {
  const q = $('#q').value.trim(), L = t(); hits.innerHTML = ''; hits.hidden = false;
  if (q.length < 2 && !/^#?\d$/.test(q)) { hits.append(el('li', 'what', L.tips)); return; }
  const { w, rows } = search(q);
  if (!rows.length) { hits.append(el('li', 'what', L.none)); return; }
  hits.append(el('li', 'what', `${L.found(rows.length)}: ${describe(w)}. ${rows.length > LIMIT ? L.more(LIMIT) : ''}`));
  for (const r of rows.slice(0, LIMIT)) {
    const li = el('li'), b = el('button'); b.type = 'button';
    const name = lang !== 'ru' && r.childEn ? [r.childEn, r.surEn].filter(Boolean).join(' ') : [r.child, (r.sur || '').split(' ').pop()].filter(Boolean).join(' ');
    const parents = lang === 'en' && r.parEn ? r.parEn : [[r.father, r.mother].filter(Boolean).join(` ${L.and} `), r.sur].filter(Boolean).join(', ');
    const dates = [r.bapt && `${L.bapt.toLowerCase()} ${showDate(r.bapt)}`, r.born && `${L.born} ${showDate(r.born)}`].filter(Boolean).join(', ') || L.noDate;
    b.innerHTML = `<b>${esc(name || L.noName)}</b><i>${r.y}${r.n ? `, ${L.no} ${r.n}` : ''}</i>
      ${parents ? `<small>${esc(parents)}</small>` : ''}${r.vil ? `<small lang="ru">${esc(r.vil)}</small>` : ''}<small>${dates}</small>`;
    b.onclick = () => { closeHits(); go(r.scan, r.row); };
    li.append(b); hits.append(li);
  }
}
$('#q').addEventListener('input', runSearch);
$('#q').addEventListener('focus', runSearch);
document.addEventListener('click', ev => { if (!ev.target.closest('.find')) closeHits(); });

lang = T[params.get('lang')] ? params.get('lang') : T[store.get('lang')] ? store.get('lang') : 'en';
closeHits(); applyLook(); setLang(lang);
// open at a random spread that has entries (a link with #s=… still opens where it points;
// the ribbon's tail leads back to the marked entry)
const randomScan = () => { const full = SPREADS.filter(m => m.n > 0); return full.length ? full[Math.floor(Math.random() * full.length)].scan : 0; };
go(+params.get('s') || randomScan() || marked.scan || BK.scan, params.get('pick'), true).then(() => { if (params.get('q')) { $('#q').value = params.get('q'); runSearch(); } if (FREEZE != null) setTimeout(() => step(1), 700); });
})();
