from django import forms
from django.forms.widgets import HiddenInput, Select

from datetime import datetime, timedelta

COUNTRIES = [('US', 'United States'),
                ('AD', 'Andorra'),
                ('AE', 'United Arab Emirates'),
                ('AF', 'Afghanistan'),
                ('AG', 'Antigua and Barbuda'),
                ('AI', 'Anguilla'),
                ('AL', 'Albania'),
                ('AM', 'Armenia'),
                ('AN', 'Netherlands Antilles'),
                ('DZ', 'Algeria'),
                ('AO', 'Angola'),
                ('AQ', 'Antarctica'),
                ('AR', 'Argentina'),
                ('AS', 'American Samoa'),
                ('AT', 'Austria'),
                ('AU', 'Australia'),
                ('AW', 'Aruba'),
                ('AX', 'Aland Island'),
                ('AZ', 'Azerbaijan'),
                ('BA', 'Bosnia and Herzegovina'),
                ('BB', 'Barbados'),
                ('BD', 'Bangladesh'),
                ('BE', 'Belgium'),
                ('BF', 'Burkina Faso'),
                ('BG', 'Bulgaria'),
                ('BH', 'Bahrain'),
                ('BI', 'Burundi'),
                ('BJ', 'Benin'),
                ('BL', 'Saint Barthelemy'),
                ('BM', 'Bermuda'),
                ('BN', 'Brunei Darussalam'),
                ('BO', 'Bolivia, Plurinational State of'),
                ('BR', 'Brazil'),
                ('BS', 'Bahamas'),
                ('BT', 'Bhutan'),
                ('BV', 'Bouvet Island'),
                ('BW', 'Botswana'),
                ('BY', 'Belarus'),
                ('BZ', 'Belize'),
                ('CA', 'Canada'),
                ('CC', 'Cocos (Keeling) Islands'),
                ('CD', 'Congo, the Democratic Republic of the'),
                ('CF', 'Central African Republic'),
                ('CG', 'Congo'),
                ('CH', 'Switzerland'),
                ('CI', 'Cote d\'Ivoire'),
                ('CK', 'Cook Islands'),
                ('CL', 'Chile'),
                ('CM', 'Cameroon'),
                ('CN', 'China'),
                ('CO', 'Colombia'),
                ('CR', 'Costa Rica'),
                ('CU', 'Cuba'),
                ('CV', 'Cape Verde'),
                ('CX', 'Christmas Island'),
                ('CY', 'Cyprus'),
                ('CZ', 'Czech Republic'),
                ('DE', 'Germany'),
                ('DJ', 'Djibouti'),
                ('DK', 'Denmark'),
                ('DM', 'Dominica'),
                ('DO', 'Dominican Republic'),
                ('EC', 'Ecuador'),
                ('EE', 'Estonia'),
                ('EG', 'Egypt'),
                ('EH', 'Western Sahara'),
                ('ER', 'Eritrea'),
                ('ES', 'Spain'),
                ('ET', 'Ethiopia'),
                ('FI', 'Finland'),
                ('FJ', 'Fiji'),
                ('FK', 'Falkland Islands (Malvinas)'),
                ('FM', 'Micronesia, Federated States of'),
                ('FO', 'Faroe Islands'),
                ('FR', 'France'),
                ('GA', 'Gabon'),
                ('GB', 'United Kingdom'),
                ('GD', 'Grenada'),
                ('GE', 'Georgia'),
                ('GF', 'French Guiana'),
                ('GG', 'Guernsey'),
                ('GH', 'Ghana'),
                ('GI', 'Gibraltar'),
                ('GL', 'Greenland'),
                ('GM', 'Gambia'),
                ('GN', 'Guinea'),
                ('GP', 'Guadeloupe'),
                ('GQ', 'Equatorial Guinea'),
                ('GR', 'Greece'),
                ('GS', 'South Georgia and the South Sandwich Islands'),
                ('GT', 'Guatemala'),
                ('GU', 'Guam'),
                ('GW', 'Guinea-Bissau'),
                ('GY', 'Guyana'),
                ('HK', 'Hong Kong'),
                ('HM', 'Heard Island and McDonald Islands'),
                ('HN', 'Honduras'),
                ('HR', 'Croatia'),
                ('HT', 'Haiti'),
                ('HU', 'Hungary'),
                ('ID', 'Indonesia'),
                ('IE', 'Ireland'),
                ('IL', 'Israel'),
                ('IM', 'Isle of Man'),
                ('IN', 'India'),
                ('IO', 'British Indian Ocean Territory'),
                ('IQ', 'Iraq'),
                ('IR', 'Iran, Islamic Republic of'),
                ('IS', 'Iceland'),
                ('IT', 'Italy'),
                ('JE', 'Jersey'),
                ('JM', 'Jamaica'),
                ('JO', 'Jordan'),
                ('JP', 'Japan'),
                ('KE', 'Kenya'),
                ('KG', 'Kyrgyzstan'),
                ('KH', 'Cambodia'),
                ('KI', 'Kiribati'),
                ('KM', 'Comoros'),
                ('KN', 'Saint Kitts and Nevis'),
                ('KP', 'Korea, Democratic People\'s Republic of'),
                ('KR', 'Korea, Republic of'),
                ('KW', 'Kuwait'),
                ('KY', 'Cayman Islands'),
                ('KZ', 'Kazakhstan'),
                ('LA', 'Lao People\'s Democratic Republic'),
                ('LB', 'Lebanon'),
                ('LC', 'Saint Lucia'),
                ('LI', 'Liechtenstein'),
                ('LK', 'Sri Lanka'),
                ('LR', 'Liberia'),
                ('LS', 'Lesotho'),
                ('LT', 'Lithuania'),
                ('LU', 'Luxembourg'),
                ('LV', 'Latvia'),
                ('LY', 'Libyan Arab Jamahiriya'),
                ('MA', 'Morocco'),
                ('MC', 'Monaco'),
                ('MD', 'Moldova, Republic of'),
                ('ME', 'Montenegro'),
                ('MF', 'Saint Martin (French part)'),
                ('MG', 'Madagascar'),
                ('MH', 'Marshall Islands'),
                ('MK', 'Macedonia, the former Yugoslav Republic of'),
                ('ML', 'Mali'),
                ('MM', 'Myanmar'),
                ('MN', 'Mongolia'),
                ('MO', 'Macao'),
                ('MP', 'Northern Mariana Islands'),
                ('MQ', 'Martinique'),
                ('MR', 'Mauritania'),
                ('MS', 'Montserrat'),
                ('MT', 'Malta'),
                ('MU', 'Mauritius'),
                ('MV', 'Maldives'),
                ('MW', 'Malawi'),
                ('MX', 'Mexico'),
                ('MY', 'Malaysia'),
                ('MZ', 'Mozambique'),
                ('NA', 'Namibia'),
                ('NC', 'New Caledonia'),
                ('NE', 'Niger'),
                ('NF', 'Norfolk Island'),
                ('NG', 'Nigeria'),
                ('NI', 'Nicaragua'),
                ('NL', 'Netherlands'),
                ('NO', 'Norway'),
                ('NP', 'Nepal'),
                ('NR', 'Nauru'),
                ('NU', 'Niue'),
                ('NZ', 'New Zealand'),
                ('OM', 'Oman'),
                ('PA', 'Panama'),
                ('PE', 'Peru'),
                ('PF', 'French Polynesia'),
                ('PG', 'Papua New Guinea'),
                ('PH', 'Philippines'),
                ('PK', 'Pakistan'),
                ('PL', 'Poland'),
                ('PM', 'Saint Pierre and Miquelon'),
                ('PN', 'Pitcairn'),
                ('PR', 'Puerto Rico'),
                ('PS', 'Palestinian Territory, Occupied'),
                ('PT', 'Portugal'),
                ('PW', 'Palau'),
                ('PY', 'Paraguay'),
                ('QA', 'Qatar'),
                ('RE', 'Reunion'),
                ('RO', 'Romania'),
                ('RS', 'Serbia'),
                ('RU', 'Russian Federation'),
                ('RW', 'Rwanda'),
                ('SA', 'Saudi Arabia'),
                ('SB', 'Solomon Islands'),
                ('SC', 'Seychelles'),
                ('SD', 'Sudan'),
                ('SE', 'Sweden'),
                ('SG', 'Singapore'),
                ('SH', 'Saint Helena, Ascension and Tristan da Cunha'),
                ('SI', 'Slovenia'),
                ('SJ', 'Svalbard and Jan Mayen'),
                ('SK', 'Slovakia'),
                ('SL', 'Sierra Leone'),
                ('SM', 'San Marino'),
                ('SN', 'Senegal'),
                ('SO', 'Somalia'),
                ('SR', 'Suriname'),
                ('ST', 'Sao Tome and Principe'),
                ('SV', 'El Salvador'),
                ('SY', 'Syrian Arab Republic'),
                ('SZ', 'Swaziland'),
                ('TC', 'Turks and Caicos Islands'),
                ('TD', 'Chad'),
                ('TF', 'French Southern Territories'),
                ('TG', 'Togo'),
                ('TH', 'Thailand'),
                ('TJ', 'Tajikistan'),
                ('TK', 'Tokelau'),
                ('TL', 'Timor-Leste'),
                ('TM', 'Turkmenistan'),
                ('TN', 'Tunisia'),
                ('TO', 'Tonga'),
                ('TR', 'Turkey'),
                ('TT', 'Trinidad and Tobago'),
                ('TV', 'Tuvalu'),
                ('TW', 'Taiwan, Province of China'),
                ('TZ', 'Tanzania, United Republic of'),
                ('UA', 'Ukraine'),
                ('UG', 'Uganda'),
                ('UM', 'United States Minor Outlying Islands'),
                ('UY', 'Uruguay'),
                ('UZ', 'Uzbekistan'),
                ('VA', 'Holy See (Vatican City State)'),
                ('VC', 'Saint Vincent and the Grenadines'),
                ('VE', 'Venezuela, Bolivarian Republic of'),
                ('VG', 'Virgin Islands, British'),
                ('VI', 'Virgin Islands, U.S.'),
                ('VN', 'Viet Nam'),
                ('VU', 'Vanuatu'),
                ('WF', 'Wallis and Futuna'),
                ('WS', 'Samoa'),
                ('YE', 'Yemen'),
                ('YT', 'Mayotte'),
                ('ZA', 'South Africa'),
                ('ZM', 'Zambia'),
                ('ZW', 'Zimbabwe'),]


def emptystyle(original_class):
    class E(original_class):
        def widget_attrs(self, widget):
            attrs = { 'class': 'empty', 'emptyvalue': self.label }
            if isinstance(widget, forms.PasswordInput):
                attrs['ispass'] = 'ispass'
            return attrs
    return E

class LoginForm(forms.Form):
    email = emptystyle(forms.EmailField)(required=True, label='Email')
    password = emptystyle(forms.CharField)(widget=forms.PasswordInput, label='Password')

class ForgotPassForm(forms.Form):
    email = emptystyle(forms.EmailField)(required=True, label='Email')

class CloseAccountForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label='Password')

class SignUpForm(forms.Form):
    email = forms.EmailField(required=True, label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    password_again = forms.CharField(widget=forms.PasswordInput, label=('Password again'))
    
    def clean_password_again(self):
        if 'password' in self.cleaned_data:
            if self.cleaned_data['password'] != self.cleaned_data['password_again']:
                raise forms.ValidationError('Passwords didn\'t match')

class ChangePassForm(forms.Form):
    old_password = emptystyle(forms.CharField)(widget=forms.PasswordInput, label='Current password')
    new_password = emptystyle(forms.CharField)(widget=forms.PasswordInput, label='New password')
    new_password_again = emptystyle(forms.CharField)(widget=forms.PasswordInput, label=('Repeat new password'))
    
    def clean_new_password_again(self):
        if 'new_password' in self.cleaned_data:
            if self.cleaned_data['new_password'] != self.cleaned_data['new_password_again']:
                raise forms.ValidationError('Passwords didn\'t match')

class IndexForm(forms.Form):
    name = emptystyle(forms.CharField)(min_length=3, max_length=50, required=True, label='Index Name')
    def clean_name(self):
        name = self.cleaned_data['name']
        if name is None or len(name) == 0:
            raise forms.ValidationError('Must provide an index name')
        if not name[0].isalpha():
            raise forms.ValidationError('Index name must start with a letter')
        for character in name:
            if not (character.isalpha() or character.isdigit() or character == '_'):
                raise forms.ValidationError('Invalid character in index name.')
        return name

class ScoreFunctionForm(forms.Form):
    name = forms.CharField(widget=HiddenInput(), min_length=1, required=True, label='Numeric Code')
    definition = forms.CharField(required=True, label='Formula')

class BetaTestForm(forms.Form):
    email = forms.EmailField(required=True, label='* E-Mail')
    site_url = forms.CharField(required=False, label='Site', max_length=200)
    textarea_widget = forms.widgets.Textarea(attrs={'rows': 5, 'cols': 20})
    summary = forms.CharField(widget=textarea_widget, required=False, max_length=500, min_length=4, label='Intended use')

class PaymentInformationForm(forms.Form):
    first_name = emptystyle(forms.CharField)(required=True, label='First Name', max_length=50)
    last_name = emptystyle(forms.CharField)(required=True, label='Last Name', max_length=50)
    
    credit_card_number = emptystyle(forms.CharField)(required=True, label='Credit Card Number', max_length=19)
    exp_month = emptystyle(forms.CharField)(required=True, label='Expiration (MM/YY)', max_length=5)
    #exp_year = emptystyle(forms.CharField)(required=True, label='Exp Year', max_length=2)

    address = emptystyle(forms.CharField)(required=False, label='Address', max_length=60)
    city = emptystyle(forms.CharField)(required=False, label='City', max_length=60)
    state = emptystyle(forms.CharField)(required=False, label='State', max_length=2)
    zip_code = emptystyle(forms.CharField)(required=False, label='ZIP Code', max_length=15)
    #select_widget = Select(attrs={'style':'width: 280px;border: none;background: white;font-size: 16px;height: 40px;margin: 1px;text-indent: 5px;'})
    country = emptystyle(forms.ChoiceField)(required=False, choices=COUNTRIES, label='Country')

    def clean_credit_card_number(self):
        if 'credit_card_number' in self.cleaned_data:
            cc = self.cleaned_data['credit_card_number']
            if not cc.isdigit() or not is_luhn_valid(cc):
                raise forms.ValidationError('Invalid credit card number')
            return self.cleaned_data['credit_card_number']
        
    def clean(self):
        month = ''
        year = ''
        if 'exp_month' in self.cleaned_data:
            month = self.cleaned_data['exp_month']
            if not '/' in month:
                self._errors['exp_month'] = ['Not a valid expiration (it should be MM/YY)']
                return
            
            month, year = month.split('/', 1)
            
            if not month.isdigit() or int(month) > 12:
                self._errors['exp_month'] = ['Not a valid expiration month (it should be MM/YY)']
                return
            if not year.isdigit() or int(year) > 99:
                self._errors['exp_month'] = ['Not a valid expiration year (it should be MM/YY)']
                return
        else:
            self._errors['exp_month'] = ['Not a valid expiration (it should be MM/YY)']
            return
                
        expiration = datetime(month=int(month), year=int('20' + year), day=1)
        today = datetime.now() + timedelta(days=1)
        
        checkpoint_month = today.month + 1 if today.month != 12 else 1
        checkpoint_year = today.year if today.month != 12 else today.year + 1
        
        checkpoint = datetime(month=checkpoint_month, year=checkpoint_year, day=1)
        
        if expiration <= checkpoint:
            self._errors['exp_month'] = ['Card expired']
            return
    
        return self.cleaned_data        

            
def is_luhn_valid(cc):
    num = map(int, cc)
    return not sum(num[::-2] + map(lambda d: sum(divmod(d * 2, 10)), num[-2::-2])) % 10


    
