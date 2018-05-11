# Copyright (C) 2017  Saiful Bari Khan <saifulbkhan@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, math

DEFAULT_THESAURUS_PATH = '/usr/share/mythes'

# ISO-3166 country codes
COUNTRIES = {
    "AF": "AFGHANISTAN",
    "AL": "ALBANIA",
    "DZ": "ALGERIA",
    "AS": "AMERICAN SAMOA",
    "AD": "ANDORRA",
    "AO": "ANGOLA",
    "AQ": "ANTARCTICA",
    "AG": "ANTIGUA AND BARBUDA",
    "AR": "ARGENTINA",
    "AM": "ARMENIA",
    "AW": "ARUBA",
    "AU": "AUSTRALIA",
    "AT": "AUSTRIA",
    "AZ": "AZERBAIJAN",
    "BS": "BAHAMAS",
    "BH": "BAHRAIN",
    "BD": "BANGLADESH",
    "BB": "BARBADOS",
    "BY": "BELARUS",
    "BE": "BELGIUM",
    "BZ": "BELIZE",
    "BJ": "BENIN",
    "BM": "BERMUDA",
    "BT": "BHUTAN",
    "BO": "BOLIVIA",
    "BA": "BOSNIA AND HERZEGOVINA",
    "BW": "BOTSWANA",
    "BV": "BOUVET ISLAND",
    "BR": "BRAZIL",
    "IO": "BRITISH INDIAN OCEAN TERRITORY",
    "BN": "BRUNEI DARUSSALAM",
    "BG": "BULGARIA",
    "BF": "BURKINA FASO",
    "BI": "BURUNDI",
    "KH": "CAMBODIA",
    "CM": "CAMEROON",
    "CA": "CANADA",
    "CV": "CAPE VERDE",
    "KY": "CAYMAN ISLANDS",
    "CF": "CENTRAL AFRICAN REPUBLIC",
    "TD": "CHAD",
    "CL": "CHILE",
    "CN": "CHINA",
    "CX": "CHRISTMAS ISLAND",
    "CC": "COCOS (KEELING) ISLANDS",
    "CO": "COLOMBIA",
    "KM": "COMOROS",
    "CG": "CONGO",
    "CD": "CONGO, THE DEMOCRATIC REPUBLIC OF THE",
    "CK": "COOK ISLANDS",
    "CR": "COSTA RICA",
    "CI": "CÔTE D'IVOIRE",
    "HR": "CROATIA",
    "CU": "CUBA",
    "CY": "CYPRUS",
    "CZ": "CZECH REPUBLIC",
    "DK": "DENMARK",
    "DJ": "DJIBOUTI",
    "DM": "DOMINICA",
    "DO": "DOMINICAN REPUBLIC",
    "EC": "ECUADOR",
    "EG": "EGYPT",
    "SV": "EL SALVADOR",
    "GQ": "EQUATORIAL GUINEA",
    "ER": "ERITREA",
    "EE": "ESTONIA",
    "ET": "ETHIOPIA",
    "FK": "FALKLAND ISLANDS (MALVINAS)",
    "FO": "FAROE ISLANDS",
    "FJ": "FIJI",
    "FI": "FINLAND",
    "FR": "FRANCE",
    "GF": "FRENCH GUIANA",
    "PF": "FRENCH POLYNESIA",
    "TF": "FRENCH SOUTHERN TERRITORIES",
    "GA": "GABON",
    "GM": "GAMBIA",
    "GE": "GEORGIA",
    "DE": "GERMANY",
    "GH": "GHANA",
    "GI": "GIBRALTAR",
    "GR": "GREECE",
    "GL": "GREENLAND",
    "GD": "GRENADA",
    "GP": "GUADELOUPE",
    "GU": "GUAM",
    "GT": "GUATEMALA",
    "GN": "GUINEA",
    "GW": "GUINEA-BISSAU",
    "GY": "GUYANA",
    "HT": "HAITI",
    "HM": "HEARD ISLAND AND MCDONALD ISLANDS",
    "HN": "HONDURAS",
    "HK": "HONG KONG",
    "HU": "HUNGARY",
    "IS": "ICELAND",
    "IN": "INDIA",
    "ID": "INDONESIA",
    "IR": "IRAN, ISLAMIC REPUBLIC OF",
    "IQ": "IRAQ",
    "IE": "IRELAND",
    "IL": "ISRAEL",
    "IT": "ITALY",
    "JM": "JAMAICA",
    "JP": "JAPAN",
    "JO": "JORDAN",
    "KZ": "KAZAKHSTAN",
    "KE": "KENYA",
    "KI": "KIRIBATI",
    "KP": "KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF",
    "KR": "KOREA, REPUBLIC OF",
    "KW": "KUWAIT",
    "KG": "KYRGYZSTAN",
    "LA": "LAO PEOPLE'S DEMOCRATIC REPUBLIC",
    "LV": "LATVIA",
    "LB": "LEBANON",
    "LS": "LESOTHO",
    "LR": "LIBERIA",
    "LY": "LIBYAN ARAB JAMAHIRIYA",
    "LI": "LIECHTENSTEIN",
    "LT": "LITHUANIA",
    "LU": "LUXEMBOURG",
    "MO": "MACAO",
    "MK": "MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF",
    "MG": "MADAGASCAR",
    "MW": "MALAWI",
    "MY": "MALAYSIA",
    "MV": "MALDIVES",
    "ML": "MALI",
    "MT": "MALTA",
    "MH": "MARSHALL ISLANDS",
    "MQ": "MARTINIQUE",
    "MR": "MAURITANIA",
    "MU": "MAURITIUS",
    "YT": "MAYOTTE",
    "MX": "MEXICO",
    "FM": "MICRONESIA, FEDERATED STATES OF",
    "MD": "MOLDOVA, REPUBLIC OF",
    "MD": "MONACO",
    "MN": "MONGOLIA",
    "MS": "MONTSERRAT",
    "MA": "MOROCCO",
    "MZ": "MOZAMBIQUE",
    "MM": "MYANMAR",
    "NA": "NAMIBIA",
    "NR": "NAURU",
    "NP": "NEPAL",
    "NL": "NETHERLANDS",
    "AN": "NETHERLANDS ANTILLES",
    "NC": "NEW CALEDONIA",
    "NZ": "NEW ZEALAND",
    "NI": "NICARAGUA",
    "NE": "NIGER",
    "NG": "NIGERIA",
    "NU": "NIUE",
    "NF": "NORFOLK ISLAND",
    "MP": "NORTHERN MARIANA ISLANDS",
    "NO": "NORWAY",
    "OM": "OMAN",
    "PK": "PAKISTAN",
    "PW": "PALAU",
    "PS": "PALESTINIAN TERRITORY, OCCUPIED",
    "PA": "PANAMA",
    "PG": "PAPUA NEW GUINEA",
    "PY": "PARAGUAY",
    "PE": "PERU",
    "PH": "PHILIPPINES",
    "PN": "PITCAIRN",
    "PL": "POLAND",
    "PR": "PUERTO RICO",
    "QA": "QATAR",
    "RE": "RÉUNION",
    "RO": "ROMANIA",
    "RU": "RUSSIAN FEDERATION",
    "RW": "RWANDA",
    "SH": "SAINT HELENA",
    "KN": "SAINT KITTS AND NEVIS",
    "LC": "SAINT LUCIA",
    "PM": "SAINT PIERRE AND MIQUELON",
    "VC": "SAINT VINCENT AND THE GRENADINES",
    "WS": "SAMOA",
    "SM": "SAN MARINO",
    "ST": "SAO TOME AND PRINCIPE",
    "SA": "SAUDI ARABIA",
    "SN": "SENEGAL",
    "CS": "SERBIA AND MONTENEGRO",
    "SC": "SEYCHELLES",
    "SL": "SIERRA LEONE",
    "SG": "SINGAPORE",
    "SK": "SLOVAKIA",
    "SI": "SLOVENIA",
    "SB": "SOLOMON ISLANDS",
    "SO": "SOMALIA",
    "ZA": "SOUTH AFRICA",
    "GS": "SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS",
    "ES": "SPAIN",
    "LK": "SRI LANKA",
    "SD": "SUDAN",
    "SR": "SURINAME",
    "SJ": "SVALBARD AND JAN MAYEN",
    "SZ": "SWAZILAND",
    "SE": "SWEDEN",
    "CH": "SWITZERLAND",
    "SY": "SYRIAN ARAB REPUBLIC",
    "TW": "TAIWAN, PROVINCE OF CHINA",
    "TJ": "TAJIKISTAN",
    "TZ": "TANZANIA, UNITED REPUBLIC OF",
    "TH": "THAILAND",
    "TL": "TIMOR-LESTE",
    "TG": "TOGO",
    "TK": "TOKELAU",
    "TO": "TONGA",
    "TT": "TRINIDAD AND TOBAGO",
    "TN": "TUNISIA",
    "TR": "TURKEY",
    "TM": "TURKMENISTAN",
    "TC": "TURKS AND CAICOS ISLANDS",
    "TV": "TUVALU",
    "UG": "UGANDA",
    "UA": "UKRAINE",
    "AE": "UNITED ARAB EMIRATES",
    "GB": "UNITED KINGDOM",
    "US": "UNITED STATES",
    "UM": "UNITED STATES MINOR OUTLYING ISLANDS",
    "UY": "URUGUAY",
    "UZ": "UZBEKISTAN",
    "VU": "VANUATU",
    "VE": "VENEZUELA",
    "VN": "VIET NAM",
    "VG": "VIRGIN ISLANDS, BRITISH",
    "VI": "VIRGIN ISLANDS, U.S.",
    "WF": "WALLIS AND FUTUNA",
    "EH": "WESTERN SAHARA",
    "YE": "YEMEN",
    "ZM": "ZAMBIA",
    "ZW": "ZIMBABWE"
}

# ISO-639 language codes
LANGUAGES = {
    "ab": "Abkhazian",
    "aa": "Afar",
    "af": "Afrikaans",
    "sq": "Albanian",
    "am": "Amharic",
    "ar": "Arabic",
    "hy": "Armenian",
    "as": "Assamese",
    "ay": "Aymara",
    "az": "Azerbaijani",
    "ba": "Bashkir",
    "eu": "Basque",
    "bn": "Bengali (Bangla)",
    "dz": "Bhutani",
    "bh": "Bihari",
    "bi": "Bislama",
    "br": "Breton",
    "bg": "Bulgarian",
    "my": "Burmese",
    "be": "Byelorussian (Belarusian)",
    "km": "Cambodian",
    "ca": "Catalan",
    "zh": "Chinese (Simplified)",
    "zh": "Chinese (Traditional)",
    "co": "Corsican",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "eo": "Esperanto",
    "et": "Estonian",
    "fo": "Faeroese",
    "fa": "Farsi",
    "fj": "Fiji",
    "fi": "Finnish",
    "fr": "French",
    "fy": "Frisian",
    "gl": "Galician",
    "gd": "Gaelic (Scottish)",
    "gv": "Gaelic (Manx)",
    "ka": "Georgian",
    "de": "German",
    "el": "Greek",
    "kl": "Greenlandic",
    "gn": "Guarani",
    "gu": "Gujarati",
    "ha": "Hausa",
    "he": "Hebrew",
    "hi": "Hindi",
    "hu": "Hungarian",
    "is": "Icelandic",
    "id": "Indonesian",
    "ia": "Interlingua",
    "ie": "Interlingue",
    "iu": "Inuktitut",
    "ik": "Inupiak",
    "ga": "Irish",
    "it": "Italian",
    "ja": "Japanese",
    "ja": "Javanese",
    "kn": "Kannada",
    "ks": "Kashmiri",
    "kk": "Kazakh",
    "rw": "Kinyarwanda (Ruanda)",
    "ky": "Kirghiz",
    "rn": "Kirundi (Rundi)",
    "ko": "Korean",
    "ku": "Kurdish",
    "lo": "Laothian",
    "la": "Latin",
    "lv": "Latvian (Lettish)",
    "li": "Limburgish ( Limburger)",
    "ln": "Lingala",
    "lt": "Lithuanian",
    "mk": "Macedonian",
    "mg": "Malagasy",
    "ms": "Malay",
    "ml": "Malayalam",
    "mt": "Maltese",
    "mi": "Maori",
    "mr": "Marathi",
    "mo": "Moldavian",
    "mn": "Mongolian",
    "na": "Nauru",
    "ne": "Nepali",
    "no": "Norwegian",
    "oc": "Occitan",
    "or": "Oriya",
    "om": "Oromo (Afan, Galla)",
    "ps": "Pashto (Pushto)",
    "pl": "Polish",
    "pt": "Portuguese",
    "pa": "Punjabi",
    "qu": "Quechua",
    "rm": "Rhaeto-Romance",
    "ro": "Romanian",
    "ru": "Russian",
    "sm": "Samoan",
    "sg": "Sangro",
    "sa": "Sanskrit",
    "sr": "Serbian",
    "sh": "Serbo-Croatian",
    "st": "Sesotho",
    "tn": "Setswana",
    "sn": "Shona",
    "sd": "Sindhi",
    "si": "Sinhalese",
    "ss": "Siswati",
    "sk": "Slovak",
    "sl": "Slovenian",
    "so": "Somali",
    "es": "Spanish",
    "su": "Sundanese",
    "sw": "Swahili (Kiswahili)",
    "sv": "Swedish",
    "tl": "Tagalog",
    "tg": "Tajik",
    "ta": "Tamil",
    "tt": "Tatar",
    "te": "Telugu",
    "th": "Thai",
    "bo": "Tibetan",
    "ti": "Tigrinya",
    "to": "Tonga",
    "ts": "Tsonga",
    "tr": "Turkish",
    "tk": "Turkmen",
    "tw": "Twi",
    "ug": "Uighur",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "vo": "Volapük",
    "cy": "Welsh",
    "wo": "Wolof",
    "xh": "Xhosa",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "zu": "Zulu"
}


def language_region_for_tag(language_tag):
    '''Expects a hyphen or underscore separated language and country codes'''
    lang_code, country = None, None

    hyphen_pos = language_tag.find('-')
    if hyphen_pos != -1:
        lang_code, country = language_tag.split('-', maxsplit=1)

    underscore_pos = language_tag.find('_')
    if underscore_pos != -1:
        lang_code, country_code = language_tag.split('_', maxsplit=1)

    language = LANGUAGES.get(lang_code)
    country = COUNTRIES.get(country_code)

    return language, country


def available_language_packs(mythes_path=DEFAULT_THESAURUS_PATH, prefix='th_', suffix='_v2'):
    '''Return a list of language tags for which thesaurus is available'''
    dat_names, idx_names = [], []

    for root, dirs, files in os.walk(mythes_path):
        for name in files:
            if name.endswith('.dat'):
                dat_names.append(name.rstrip('.dat'))
            if name.endswith('.idx'):
                idx_names.append(name.rstrip('.idx'))

    # only consider those packs that have both idx and dat files available
    valid_thesauri = set(dat_names) & set(idx_names)

    # strip and return names of languages available (with .dat and .idx files)
    tags = []
    for name in valid_thesauri:
        if name.startswith(prefix) and name.endswith(suffix):
            language_tag = name.lstrip(prefix).rstrip(suffix)
            tags.append(language_tag)

    return tags


# TODO: Provide a function to check the default language set for user session.
def current_user_language():
    '''Returns the language tag and encoding in use for current user'''
    language_with_encoding = os.environ['LANG']
    language, encoding = language_with_encoding.split('.', maxsplit=1)
    return language, encoding


def thes_file_encoding(fpath):
    with open(fpath, 'r', errors='surrogateescape') as f:
        # obtain character encoding for index file
        return f.readline().strip()


def byte_offset_for_word(word, index_path):
    '''Returns the byte offset in data file for given word. This involves
    performing a binary search in the index file whose path is provided.'''
    encoding = thes_file_encoding(index_path)
    with open(index_path, 'r', encoding=encoding) as f:
        # Read in the file once and build a list of line offsets
        line_offsets = []
        offset = 0
        for line in f:
            line_offsets.append(offset)
            offset += len(line.encode(encoding))

        # this value should ideally be obtained from the second line,
        # but if the structure of the index file is correct, then the
        # following should calculate the same value
        num_words = len(line_offsets) - 2

        def word_and_byte_at(offset):
            offset += 2
            if offset > (num_words-1) or offset < 2:
                return None, None

            f.seek(line_offsets[offset])
            line = f.readline().strip()

            if line.find('|') == -1:
                return None, None

            word, byte_offset = line.split('|', maxsplit=1)
            return word, int(byte_offset)

        left = 0
        right = num_words - 1
        while left < right:
            middle = math.ceil((left + right) / 2)
            word_at_middle, _ = word_and_byte_at(middle)
            if word_at_middle > word:
                right = middle - 1
            elif word_at_middle <= word:
                left = middle

        # left and right should be same now, can check for either
        final_word, byte_offset = word_and_byte_at(right)
        if final_word == word:
            return byte_offset

        return -1


def get_synonymous_words(word, language_tag):
    '''A function that takes in a word and a language tag and returns a list of
    parts-of-speech paired with a list of synonyms for each sense available.'''
    suffix = 'th_'
    prefix = '_v2'
    thesaurus_name = suffix + language_tag + prefix

    index_file_path = os.path.join(DEFAULT_THESAURUS_PATH, thesaurus_name + '.idx')
    data_file_path = os.path.join(DEFAULT_THESAURUS_PATH, thesaurus_name + '.dat')

    byte_offset = byte_offset_for_word(word, index_file_path)
    if byte_offset == -1:
        return None

    encoding = thes_file_encoding(data_file_path)
    with open(data_file_path, 'r', encoding=encoding) as dat_file:
        dat_file.seek(byte_offset)
        word_at_offset, num_senses = dat_file.readline().strip().split('|', 1)
        if not word_at_offset == word:
            return None

        synsets = []
        for i in range(int(num_senses)):
            synset = dat_file.readline().strip().split('|')
            pos = synset.pop(0)
            pos = pos.strip('()')
            pos = pos.split()
            synsets.append((pos, synset))

        return synsets
