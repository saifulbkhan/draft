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

import os, math, unicodedata

DEFAULT_THESAURUS_PATH = '/usr/share/mythes'

# ISO-3166 country codes
COUNTRIES = {
    'AD': 'Andorra',
    'AE': 'United Arab Emirates',
    'AF': 'Afghanistan',
    'AG': 'Antigua and Barbuda',
    'AL': 'Albania',
    'AM': 'Armenia',
    'AN': 'Netherlands Antilles',
    'AO': 'Angola',
    'AQ': 'Antarctica',
    'AR': 'Argentina',
    'AS': 'American Samoa',
    'AT': 'Austria',
    'AU': 'Australia',
    'AW': 'Aruba',
    'AZ': 'Azerbaijan',
    'BA': 'Bosnia and Herzegovina',
    'BB': 'Barbados',
    'BD': 'Bangladesh',
    'BE': 'Belgium',
    'BF': 'Burkina Faso',
    'BG': 'Bulgaria',
    'BH': 'Bahrain',
    'BI': 'Burundi',
    'BJ': 'Benin',
    'BM': 'Bermuda',
    'BN': 'Brunei Darussalam',
    'BO': 'Bolivia',
    'BR': 'Brazil',
    'BS': 'Bahamas',
    'BT': 'Bhutan',
    'BV': 'Bouvet Island',
    'BW': 'Botswana',
    'BY': 'Belarus',
    'BZ': 'Belize',
    'CA': 'Canada',
    'CC': 'Cocos (Keeling) Islands',
    'CD': 'Congo, The Democratic Republic of the',
    'CF': 'Central African Republic',
    'CG': 'Congo',
    'CH': 'Switzerland',
    'CI': "Côte d'Ivoire",
    'CK': 'Cook Islands',
    'CL': 'Chile',
    'CM': 'Cameroon',
    'CN': 'China',
    'CO': 'Colombia',
    'CR': 'Costa Rica',
    'CS': 'Serbia and Montenegro',
    'CU': 'Cuba',
    'CV': 'Cape Verde',
    'CX': 'Christmas Island',
    'CY': 'Cyprus',
    'CZ': 'Czech Republic',
    'DE': 'Germany',
    'DJ': 'Djibouti',
    'DK': 'Denmark',
    'DM': 'Dominica',
    'DO': 'Dominican Republic',
    'DZ': 'Algeria',
    'EC': 'Ecuador',
    'EE': 'Estonia',
    'EG': 'Egypt',
    'EH': 'Western Sahara',
    'ER': 'Eritrea',
    'ES': 'Spain',
    'ET': 'Ethiopia',
    'FI': 'Finland',
    'FJ': 'Fiji',
    'FK': 'Falkland Islands (Malvinas)',
    'FM': 'Micronesia, Federated States of',
    'FO': 'Faroe Islands',
    'FR': 'France',
    'GA': 'Gabon',
    'GB': 'United Kingdom',
    'GD': 'Grenada',
    'GE': 'Georgia',
    'GF': 'French Guiana',
    'GH': 'Ghana',
    'GI': 'Gibraltar',
    'GL': 'Greenland',
    'GM': 'Gambia',
    'GN': 'Guinea',
    'GP': 'Guadeloupe',
    'GQ': 'Equatorial Guinea',
    'GR': 'Greece',
    'GS': 'South Georgia and the South Sandwich Islands',
    'GT': 'Guatemala',
    'GU': 'Guam',
    'GW': 'Guinea-Bissau',
    'GY': 'Guyana',
    'HK': 'Hong Kong',
    'HM': 'Heard Island and McDonald Islands',
    'HN': 'Honduras',
    'HR': 'Croatia',
    'HT': 'Haiti',
    'HU': 'Hungary',
    'ID': 'Indonesia',
    'IE': 'Ireland',
    'IL': 'Israel',
    'IN': 'India',
    'IO': 'British Indian Ocean Territory',
    'IQ': 'Iraq',
    'IR': 'Iran, Islamic Republic of',
    'IS': 'Iceland',
    'IT': 'Italy',
    'JM': 'Jamaica',
    'JO': 'Jordan',
    'JP': 'Japan',
    'KE': 'Kenya',
    'KG': 'Kyrgyzstan',
    'KH': 'Cambodia',
    'KI': 'Kiribati',
    'KM': 'Comoros',
    'KN': 'Saint Kitts and Nevis',
    'KP': "Korea, Democratic People's Republic of",
    'KR': 'Korea, Republic of',
    'KW': 'Kuwait',
    'KY': 'Cayman Islands',
    'KZ': 'Kazakhstan',
    'LA': "Lao People's Democratic Republic",
    'LB': 'Lebanon',
    'LC': 'Saint lucia',
    'LI': 'Liechtenstein',
    'LK': 'Sri lanka',
    'LR': 'Liberia',
    'LS': 'Lesotho',
    'LT': 'Lithuania',
    'LU': 'Luxembourg',
    'LV': 'Latvia',
    'LY': 'Libyan Arab Jamahiriya',
    'MA': 'Morocco',
    'MD': 'Monaco',
    'MG': 'Madagascar',
    'MH': 'Marshall Islands',
    'MK': 'Macedonia, The Former Yugoslav Republic of',
    'ML': 'Mali',
    'MM': 'Myanmar',
    'MN': 'Mongolia',
    'MO': 'Macao',
    'MP': 'Northern Mariana Islands',
    'MQ': 'Martinique',
    'MR': 'Mauritania',
    'MS': 'Montserrat',
    'MT': 'Malta',
    'MU': 'Mauritius',
    'MV': 'Maldives',
    'MW': 'Malawi',
    'MX': 'Mexico',
    'MY': 'Malaysia',
    'MZ': 'Mozambique',
    'NA': 'Namibia',
    'NC': 'New Caledonia',
    'NE': 'Niger',
    'NF': 'Norfolk Island',
    'NG': 'Nigeria',
    'NI': 'Nicaragua',
    'NL': 'Netherlands',
    'NO': 'Norway',
    'NP': 'Nepal',
    'NR': 'Nauru',
    'NU': 'Niue',
    'NZ': 'New Zealand',
    'OM': 'Oman',
    'PA': 'Panama',
    'PE': 'Peru',
    'PF': 'French Polynesia',
    'PG': 'Papua New Guinea',
    'PH': 'Philippines',
    'PK': 'Pakistan',
    'PL': 'Poland',
    'PM': 'Saint Pierre and Miquelon',
    'PN': 'Pitcairn',
    'PR': 'Puerto Rico',
    'PS': 'Palestinian Territory, Occupied',
    'PW': 'Palau',
    'PY': 'Paraguay',
    'QA': 'Qatar',
    'RE': 'Réunion',
    'RO': 'Romania',
    'RU': 'Russian Federation',
    'RW': 'Rwanda',
    'SA': 'Saudi Arabia',
    'SB': 'Solomon Islands',
    'SC': 'Seychelles',
    'SD': 'Sudan',
    'SE': 'Sweden',
    'SG': 'Singapore',
    'SH': 'Saint Helena',
    'SI': 'Slovenia',
    'SJ': 'Svalbard and Jan Mayen',
    'SK': 'Slovakia',
    'SL': 'Sierra Leone',
    'SM': 'San Marino',
    'SN': 'Senegal',
    'SO': 'Somalia',
    'SR': 'Suriname',
    'ST': 'Sao Tome and Principe',
    'SV': 'El Salvador',
    'SY': 'Syrian Arab Republic',
    'SZ': 'Swaziland',
    'TC': 'Turks and Caicos Islands',
    'TD': 'Chad',
    'TF': 'French Southern Territories',
    'TG': 'Togo',
    'TH': 'Thailand',
    'TJ': 'Tajikistan',
    'TK': 'Tokelau',
    'TL': 'Timor-leste',
    'TM': 'Turkmenistan',
    'TN': 'Tunisia',
    'TO': 'Tonga',
    'TR': 'Turkey',
    'TT': 'Trinidad and Tobago',
    'TV': 'Tuvalu',
    'TW': 'Taiwan, Province of China',
    'TZ': 'Tanzania, United Republic of',
    'UA': 'Ukraine',
    'UG': 'Uganda',
    'UM': 'United States Minor Outlying Islands',
    'US': 'United States',
    'UY': 'Uruguay',
    'UZ': 'Uzbekistan',
    'VC': 'Saint Vincent and the Grenadines',
    'VE': 'Venezuela',
    'VG': 'Virgin Islands, British',
    'VI': 'Virgin Islands, U.S.',
    'VN': 'Viet nam',
    'VU': 'Vanuatu',
    'WF': 'Wallis and Futuna',
    'WS': 'Samoa',
    'YE': 'Yemen',
    'YT': 'Mayotte',
    'ZA': 'South africa',
    'ZM': 'Zambia',
    'ZW': 'Zimbabwe'
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
    "nb": "Norwegian Bokmål",
    "nn": "Norwegian Nynorsk",
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


def normalize_caseless(text):
    '''Normalize a string using NFKD algorithm and then casefold -- suitable for
    caseless unicode comparison.'''
    return unicodedata.normalize("NFKD", text.casefold())


def compare_caseless(left, right):
    '''Compares two strings in case-insensitive and accent-insensitive way.'''
    assert isinstance(left, str) and isinstance(right, str)

    caseless_left = normalize_caseless(left)
    caseless_right = normalize_caseless(right)

    if caseless_left == caseless_right:
        return 0
    elif caseless_left > caseless_right:
        return 1
    elif caseless_left < caseless_right:
        return -1

    return None


def less_than(left, right):
    return compare_caseless(left, right) < 0


def greater_than(left, right):
    return compare_caseless(left, right) > 0


def is_equal(left, right):
    return compare_caseless(left, right) == 0


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
            if greater_than(word_at_middle, word):
                right = middle - 1
            elif less_than(word_at_middle, word) or is_equal(word_at_middle, word):
                left = middle

        # left and right should be same now, can check for either
        final_word, byte_offset = word_and_byte_at(right)
        if is_equal(final_word, word):
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
        if not is_equal(word_at_offset, word):
            return None

        synsets = []
        for i in range(int(num_senses)):
            synset = dat_file.readline().strip().split('|')
            pos = synset.pop(0)
            synsets.append((pos, synset))

        return synsets
