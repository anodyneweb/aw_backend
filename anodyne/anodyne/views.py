import logging

from django.http import HttpResponseBadRequest, JsonResponse
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import F
from api.models import State, City, Registration, Category, Reading, \
    Station
from api.serializers import RegistrationSerializer
import pandas as pd
from datetime import datetime, timedelta

log = logging.getLogger('vepolink')


def add_state_city():
    STATE_N_CITY = {
        'Delhi': ['Delhi', 'New Delhi'],
        'Karnataka': ['Bengaluru', 'Hubli-Dharwad',
                      'Belagavi', 'Mangaluru',
                      'Davanagere', 'Ballari', 'Tumkur', 'Shivamogga',
                      'Raayachuru', 'Robertson Pet', 'Kolar', 'Mandya',
                      'Udupi',
                      'Chikkamagaluru', 'Karwar', 'Ranebennuru',
                      'Ranibennur',
                      'Ramanagaram', 'Gokak', 'Yadgir',
                      'Rabkavi Banhatti',
                      'Shahabad', 'Sirsi', 'Sindhnur', 'Tiptur',
                      'Arsikere',
                      'Nanjangud', 'Sagara', 'Sira', 'Puttur', 'Athni',
                      'Mulbagal',
                      'Surapura', 'Siruguppa', 'Mudhol', 'Sidlaghatta',
                      'Shahpur',
                      'Saundatti-Yellamma', 'Wadi', 'Manvi',
                      'Nelamangala',
                      'Lakshmeshwar', 'Ramdurg', 'Nargund', 'Tarikere',
                      'Malavalli', 'Savanur', 'Lingsugur',
                      'Vijayapura',
                      'Sankeshwara', 'Madikeri', 'Talikota', 'Sedam',
                      'Shikaripur',
                      'Mahalingapura', 'Mudalagi', 'Muddebihal',
                      'Pavagada',
                      'Malur', 'Sindhagi', 'Sanduru', 'Afzalpur',
                      'Maddur',
                      'Madhugiri', 'Tekkalakote', 'Terdal',
                      'Mudabidri', 'Magadi',
                      'Navalgund', 'Shiggaon', 'Shrirangapattana',
                      'Sindagi',
                      'Sakaleshapura', 'Srinivaspur', 'Ron',
                      'Mundargi',
                      'Sadalagi', 'Piriyapatna', 'Adyar'],
        'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara',
                    'Rajkot', 'Bhavnagar',
                    'Jamnagar', 'Nadiad', 'Porbandar', 'Anand',
                    'Morvi',
                    'Mahesana', 'Bharuch', 'Vapi', 'Navsari',
                    'Veraval', 'Bhuj',
                    'Godhra', 'Palanpur', 'Valsad', 'Patan', 'Deesa',
                    'Amreli',
                    'Anjar', 'Dhoraji', 'Khambhat', 'Mahuva', 'Keshod',
                    'Wadhwan',
                    'Ankleshwar', 'Savarkundla', 'Kadi', 'Visnagar',
                    'Upleta',
                    'Una', 'Sidhpur', 'Unjha', 'Mangrol', 'Viramgam',
                    'Modasa',
                    'Palitana', 'Petlad', 'Kapadvanj', 'Sihor',
                    'Wankaner',
                    'Limbdi', 'Mandvi', 'Thangadh', 'Vyara', 'Padra',
                    'Lunawada',
                    'Rajpipla', 'Vapi', 'Umreth', 'Sanand', 'Rajula',
                    'Radhanpur',
                    'Mahemdabad', 'Ranavav', 'Tharad', 'Mansa',
                    'Umbergaon',
                    'Talaja', 'Vadnagar', 'Manavadar', 'Salaya',
                    'Vijapur',
                    'Pardi', 'Rapar', 'Songadh', 'Lathi', 'Adalaj',
                    'Chhapra'],
        'Madhya Pradesh': ['Indore', 'Bhopal', 'Jabalpur',
                           'Gwalior', 'Ujjain', 'Sagar', 'Dewas', 'Satna',
                           'Ratlam', 'Rewa', 'Murwara (Katni)', 'Singrauli',
                           'Burhanpur', 'Khandwa', 'Bhind', 'Chhindwara',
                           'Guna',
                           'Shivpuri', 'Vidisha', 'Chhatarpur', 'Damoh',
                           'Mandsaur', 'Khargone', 'Neemuch', 'Pithampur',
                           'Hoshangabad', 'Itarsi', 'Sehore', 'Betul', 'Seoni',
                           'Datia', 'Nagda'],
        'Telangana': ['Hyderabad', 'Warangal',
                      'Nizamabad', 'Karimnagar',
                      'Ramagundam', 'Khammam', 'Mahbubnagar',
                      'Mancherial',
                      'Adilabad', 'Suryapet', 'Jagtial', 'Miryalaguda',
                      'Nirmal',
                      'Kamareddy', 'Kothagudem', 'Bodhan', 'Palwancha',
                      'Mandamarri', 'Koratla', 'Sircilla', 'Tandur',
                      'Siddipet',
                      'Wanaparthy', 'Kagaznagar', 'Gadwal',
                      'Sangareddy',
                      'Bellampalle', 'Bhongir', 'Vikarabad', 'Jangaon',
                      'Bhadrachalam', 'Bhainsa', 'Farooqnagar',
                      'Medak',
                      'Narayanpet', 'Sadasivpet', 'Yellandu',
                      'Manuguru',
                      'Kyathampalle', 'Nagarkurnool'],
        'Tamil Nadu': ['Chennai', 'Coimbatore',
                       'Madurai', 'Tiruchirappalli',
                       'Salem', 'Tirunelveli', 'Tiruppur', 'Ranipet',
                       'Nagercoil',
                       'Thanjavur', 'Vellore', 'Kancheepuram', 'Erode',
                       'Tiruvannamalai', 'Pollachi', 'Rajapalayam',
                       'Sivakasi',
                       'Pudukkottai', 'Neyveli (TS)', 'Nagapattinam',
                       'Viluppuram',
                       'Tiruchengode', 'Vaniyambadi',
                       'Theni Allinagaram',
                       'Udhagamandalam', 'Aruppukkottai', 'Paramakudi',
                       'Arakkonam', 'Virudhachalam', 'Srivilliputhur',
                       'Tindivanam', 'Virudhunagar', 'Karur',
                       'Valparai',
                       'Sankarankovil', 'Tenkasi', 'Palani',
                       'Pattukkottai',
                       'Tirupathur', 'Ramanathapuram',
                       'Udumalaipettai',
                       'Gobichettipalayam', 'Thiruvarur',
                       'Thiruvallur', 'Panruti',
                       'Namakkal', 'Thirumangalam',
                       'Vikramasingapuram',
                       'Nellikuppam', 'Rasipuram', 'Tiruttani',
                       'Nandivaram-Guduvancheri', 'Periyakulam',
                       'Pernampattu',
                       'Vellakoil', 'Sivaganga', 'Vadalur',
                       'Rameshwaram',
                       'Tiruvethipuram', 'Perambalur', 'Usilampatti',
                       'Vedaranyam',
                       'Sathyamangalam', 'Puliyankudi', 'Nanjikottai',
                       'Thuraiyur',
                       'Sirkali', 'Tiruchendur', 'Periyasemur',
                       'Sattur',
                       'Vandavasi', 'Tharamangalam', 'Tirukkoyilur',
                       'Oddanchatram', 'Palladam', 'Vadakkuvalliyur',
                       'Tirukalukundram', 'Uthamapalayam', 'Surandai',
                       'Sankari',
                       'Shenkottai', 'Vadipatti', 'Sholingur',
                       'Tirupathur',
                       'Manachanallur', 'Viswanatham', 'Polur',
                       'Panagudi',
                       'Uthiramerur', 'Thiruthuraipoondi',
                       'Pallapatti', 'Ponneri',
                       'Lalgudi', 'Natham', 'Unnamalaikadai',
                       'P.N.Patti',
                       'Tharangambadi', 'Tittakudi', 'Pacode',
                       "O' Valley",
                       'Suriyampalayam', 'Sholavandan', 'Thammampatti',
                       'Namagiripettai', 'Peravurani', 'Parangipettai',
                       'Pudupattinam', 'Pallikonda', 'Sivagiri',
                       'Punjaipugalur',
                       'Padmanabhapuram', 'Thirupuvanam'],
        'West Bengal': ['Kolkata', 'Siliguri',
                        'Asansol', 'Raghunathganj',
                        'Kharagpur', 'Naihati', 'English Bazar',
                        'Baharampur',
                        'Hugli-Chinsurah', 'Raiganj', 'Jalpaiguri',
                        'Santipur',
                        'Balurghat', 'Medinipur', 'Habra', 'Ranaghat',
                        'Bankura',
                        'Nabadwip', 'Darjiling', 'Purulia', 'Arambagh',
                        'Tamluk',
                        'AlipurdUrban Agglomerationr', 'Suri',
                        'Jhargram',
                        'Gangarampur', 'Rampurhat', 'Kalimpong',
                        'Sainthia',
                        'Taki', 'Murshidabad', 'Memari',
                        'Paschim Punropara',
                        'Tarakeswar', 'Sonamukhi',
                        'PandUrban Agglomeration',
                        'Mainaguri', 'Malda', 'Panchla',
                        'Raghunathpur',
                        'Mathabhanga', 'Monoharpur', 'Srirampore',
                        'Adra'],
        'Rajasthan': ['Jaipur', 'Jodhpur', 'Bikaner',
                      'Udaipur', 'Ajmer',
                      'Bhilwara', 'Alwar', 'Bharatpur', 'Pali',
                      'Barmer', 'Sikar',
                      'Tonk', 'Sadulpur', 'Sawai Madhopur', 'Nagaur',
                      'Makrana',
                      'Sujangarh', 'Sardarshahar', 'Ladnu',
                      'Ratangarh', 'Nokha',
                      'Nimbahera', 'Suratgarh', 'Rajsamand',
                      'Lachhmangarh',
                      'Rajgarh (Churu)', 'Nasirabad', 'Nohar',
                      'Phalodi',
                      'Nathdwara', 'Pilani', 'Merta City', 'Sojat',
                      'Neem-Ka-Thana', 'Sirohi', 'Pratapgarh',
                      'Rawatbhata',
                      'Sangaria', 'Lalsot', 'Pilibanga', 'Pipar City',
                      'Taranagar',
                      'Sumerpur', 'Sagwara', 'Ramganj Mandi',
                      'Lakheri',
                      'Udaipurwati', 'Losal', 'Sri Madhopur',
                      'Ramngarh',
                      'Rawatsar', 'Rajakhera', 'Shahpura', 'Shahpura',
                      'Raisinghnagar', 'Malpura', 'Nadbai', 'Sanchore',
                      'Nagar',
                      'Rajgarh (Alwar)', 'Sheoganj', 'Sadri',
                      'Todaraisingh',
                      'Todabhim', 'Reengus', 'Rajaldesar',
                      'Sadulshahar',
                      'Sambhar', 'Prantij', 'Mount Abu', 'Mangrol',
                      'Phulera',
                      'Mandawa', 'Pindwara', 'Mandalgarh',
                      'Takhatgarh'],
        'Uttar Pradesh': ['Lucknow', 'Kanpur',
                          'Firozabad', 'Agra', 'Meerut',
                          'Varanasi', 'Allahabad', 'Amroha',
                          'Moradabad',
                          'Aligarh', 'Saharanpur', 'Noida', 'Loni',
                          'Jhansi', 'Ghaziabad',
                          'Shahjahanpur', 'Rampur', 'Modinagar',
                          'Hapur', 'Etawah',
                          'Sambhal', 'Orai', 'Bahraich', 'Unnao',
                          'Rae Bareli',
                          'Lakhimpur', 'Sitapur', 'Lalitpur',
                          'Pilibhit',
                          'Chandausi', 'Hardoi', 'Azamgarh', 'Khair',
                          'Sultanpur',
                          'Tanda', 'Nagina', 'Shamli', 'Najibabad',
                          'Shikohabad',
                          'Sikandrabad', 'Pilkhuwa', 'Renukoot',
                          'Vrindavan',
                          'Ujhani', 'Laharpur', 'Tilhar', 'Sahaswan',
                          'Rath',
                          'Sherkot', 'Kalpi', 'Tundla', 'Sandila',
                          'Nanpara',
                          'Sardhana', 'Nehtaur', 'Seohara', 'Padrauna',
                          'Mathura',
                          'Thakurdwara', 'Nawabganj', 'Siana',
                          'Noorpur',
                          'Sikandra Rao', 'Puranpur', 'Rudauli',
                          'Thana Bhawan',
                          'Palia Kalan', 'Zaidpur', 'Nautanwa',
                          'Zamania',
                          'Naugawan Sadat', 'Fatehpur Sikri',
                          'Robertsganj',
                          'Utraula', 'Sadabad', 'Rasra', 'Lar',
                          'Lal Gopalganj Nindaura', 'Sirsaganj',
                          'Pihani',
                          'Rudrapur', 'Soron', 'SUrban Agglomerationr',
                          'Samdhan',
                          'Sahjanwa', 'Rampur Maniharan', 'Sumerpur',
                          'Shahganj',
                          'Tulsipur', 'Tirwaganj',
                          'PurqUrban Agglomerationzi',
                          'Warhapur', 'Powayan', 'Sandi', 'Achhnera',
                          'Naraura',
                          'Nakur', 'Sahaspur', 'Safipur', 'Reoti',
                          'Sikanderpur',
                          'Saidpur', 'Sirsi', 'Purwa', 'Parasi',
                          'Lalganj',
                          'Phulpur', 'Shishgarh', 'Sahawar', 'Samthar',
                          'Pukhrayan', 'Obra', 'Niwai'],
        'Bihar': ['Patna', 'Gaya', 'Bhagalpur',
                  'Muzaffarpur', 'Darbhanga',
                  'Arrah', 'Begusarai', 'Chhapra', 'Katihar', 'Munger',
                  'Purnia',
                  'Saharsa', 'Sasaram', 'Hajipur', 'Dehri-on-Sone',
                  'Bettiah',
                  'Motihari', 'Bagaha', 'Siwan', 'Kishanganj',
                  'Jamalpur', 'Buxar',
                  'Jehanabad', 'Aurangabad', 'Lakhisarai', 'Nawada',
                  'Jamui',
                  'Sitamarhi', 'Araria', 'Gopalganj', 'Madhubani',
                  'Masaurhi',
                  'Samastipur', 'Mokameh', 'Supaul', 'Dumraon',
                  'Arwal',
                  'Forbesganj', 'BhabUrban Agglomeration',
                  'Narkatiaganj',
                  'Naugachhia', 'Madhepura', 'Sheikhpura',
                  'Sultanganj',
                  'Raxaul Bazar', 'Ramnagar', 'Mahnar Bazar',
                  'Warisaliganj',
                  'Revelganj', 'Rajgir', 'Sonepur', 'Sherghati',
                  'Sugauli',
                  'Makhdumpur', 'Maner', 'Rosera', 'Nokha', 'Piro',
                  'Rafiganj',
                  'Marhaura', 'Mirganj', 'Lalganj', 'Murliganj',
                  'Motipur',
                  'Manihari', 'Sheohar', 'Maharajganj', 'Silao',
                  'Barh',
                  'Asarganj'],
        'Andhra Pradesh': ['Visakhapatnam',
                           'Vijayawada', 'Guntur', 'Nellore',
                           'Kurnool', 'Rajahmundry', 'Kakinada',
                           'Tirupati',
                           'Anantapur', 'Kadapa', 'Vizianagaram',
                           'Eluru',
                           'Ongole', 'Nandyal', 'Machilipatnam',
                           'Adoni', 'Tenali',
                           'Chittoor', 'Hindupur', 'Proddatur',
                           'Bhimavaram',
                           'Madanapalle', 'Guntakal', 'Dharmavaram',
                           'Gudivada',
                           'Srikakulam', 'Narasaraopet', 'Rajampet',
                           'Tadpatri',
                           'Tadepalligudem', 'Chilakaluripet',
                           'Yemmiganur',
                           'Kadiri', 'Chirala', 'Anakapalle', 'Kavali',
                           'Palacole',
                           'Sullurpeta', 'Tanuku', 'Rayachoti',
                           'Srikalahasti',
                           'Bapatla', 'Naidupet', 'Nagari', 'Gudur',
                           'Vinukonda',
                           'Narasapuram', 'Nuzvid', 'Markapur',
                           'Ponnur',
                           'Kandukur', 'Bobbili', 'Rayadurg',
                           'Samalkot',
                           'Jaggaiahpet', 'Tuni', 'Amalapuram',
                           'Bheemunipatnam',
                           'Venkatagiri', 'Sattenapalle', 'Pithapuram',
                           'Palasa Kasibugga', 'Parvathipuram',
                           'Macherla',
                           'Gooty', 'Salur', 'Mandapeta',
                           'Jammalamadugu',
                           'Peddapuram', 'Punganur', 'Nidadavole',
                           'Repalle',
                           'Ramachandrapuram', 'Kovvur', 'Tiruvuru',
                           'Uravakonda',
                           'Narsipatnam', 'Yerraguntla', 'Pedana',
                           'Puttur',
                           'Renigunta', 'Rajam',
                           'Srisailam Project (Right Flank Colony) Township'],
        'Punjab': ['Ludhiana', 'Patiala', 'Amritsar',
                   'Jalandhar', 'Bathinda',
                   'Pathankot', 'Hoshiarpur', 'Batala', 'Moga',
                   'Malerkotla',
                   'Khanna', 'Mohali', 'Barnala', 'Firozpur',
                   'Phagwara',
                   'Kapurthala', 'Zirakpur', 'Kot Kapura', 'Faridkot',
                   'Muktsar',
                   'Rajpura', 'Sangrur', 'Fazilka', 'Gurdaspur',
                   'Kharar',
                   'Gobindgarh', 'Mansa', 'Malout', 'Nabha',
                   'Tarn Taran',
                   'Jagraon', 'Sunam', 'Dhuri', 'Firozpur Cantt.',
                   'Sirhind Fatehgarh Sahib', 'Rupnagar',
                   'Jalandhar Cantt.',
                   'Samana', 'Nawanshahr', 'Rampura Phul', 'Nangal',
                   'Nakodar',
                   'Zira', 'Patti', 'Raikot', 'Longowal',
                   'Urmar Tanda',
                   'Phillaur', 'Pattran', 'Qadian', 'Sujanpur',
                   'Mukerian',
                   'Talwara'],
        'Haryana': ['Faridabad', 'Gurgaon', 'Hisar',
                    'Rohtak', 'Panipat', 'Karnal',
                    'Sonipat', 'Yamunanagar', 'Panchkula', 'Bhiwani',
                    'Bahadurgarh', 'Jind', 'Sirsa', 'Thanesar',
                    'Kaithal',
                    'Palwal', 'Rewari', 'Hansi', 'Narnaul',
                    'Fatehabad', 'Gohana',
                    'Tohana', 'Narwana', 'Mandi Dabwali',
                    'Charkhi Dadri',
                    'Shahbad', 'Pehowa', 'Samalkha', 'Pinjore',
                    'Ladwa', 'Sohna',
                    'Safidon', 'Taraori', 'Mahendragarh', 'Ratia',
                    'Rania',
                    'Sarsod'],
        'Chhattisgarh': ['Raipur', 'Bhilai Nagar',
                         'Korba', 'Bilaspur', 'Durg',
                         'Rajnandgaon', 'Jagdalpur', 'Raigarh',
                         'Ambikapur',
                         'Mahasamund', 'Dhamtari', 'Chirmiri',
                         'Bhatapara',
                         'Dalli-Rajhara', 'Naila Janjgir',
                         'Tilda Newra',
                         'Mungeli', 'Manendragarh', 'Sakti'],
        'Assam': ['Guwahati', 'Silchar', 'Dibrugarh',
                  'Nagaon', 'Tinsukia',
                  'Jorhat', 'Bongaigaon City', 'Dhubri', 'Diphu',
                  'North Lakhimpur', 'Tezpur', 'Karimganj', 'Sibsagar',
                  'Goalpara',
                  'Barpeta', 'Lanka', 'Lumding', 'Mankachar',
                  'Nalbari', 'Rangia',
                  'Margherita', 'Mangaldoi', 'Silapathar', 'Mariani',
                  'Marigaon'],
        'Chandigarh': ['Chandigarh'],
        'Odisha': ['Bhubaneswar', 'Cuttack',
                   'Raurkela', 'Brahmapur', 'Sambalpur',
                   'Puri', 'Baleshwar Town', 'Baripada Town',
                   'Bhadrak',
                   'Balangir', 'Jharsuguda', 'Bargarh', 'Paradip',
                   'Bhawanipatna',
                   'Dhenkanal', 'Barbil', 'Kendujhar', 'Sunabeda',
                   'Rayagada',
                   'Jatani', 'Byasanagar', 'Kendrapara',
                   'Rajagangapur',
                   'Parlakhemundi', 'Talcher', 'Sundargarh',
                   'Phulabani',
                   'Pattamundai', 'Titlagarh', 'Nabarangapur', 'Soro',
                   'Malkangiri', 'Rairangpur', 'Tarbha'],
        'Kerala': ['Thiruvananthapuram', 'Kochi',
                   'Kozhikode', 'Kollam',
                   'Thrissur', 'Palakkad', 'Alappuzha', 'Malappuram',
                   'Ponnani',
                   'Vatakara', 'Kanhangad', 'Taliparamba', 'Koyilandy',
                   'Neyyattinkara', 'Kayamkulam', 'Nedumangad',
                   'Kannur', 'Tirur',
                   'Kottayam', 'Kasaragod', 'Kunnamkulam',
                   'Ottappalam',
                   'Thiruvalla', 'Thodupuzha', 'Chalakudy',
                   'Changanassery',
                   'Punalur', 'Nilambur', 'Cherthala',
                   'Perinthalmanna',
                   'Mattannur', 'Shoranur', 'Varkala', 'Paravoor',
                   'Pathanamthitta', 'Peringathur', 'Attingal',
                   'Kodungallur',
                   'Pappinisseri', 'Chittur-Thathamangalam',
                   'Muvattupuzha',
                   'Adoor', 'Mavelikkara', 'Mavoor', 'Perumbavoor',
                   'Vaikom',
                   'Palai', 'Panniyannur', 'Guruvayoor', 'Puthuppally',
                   'Panamattom'],
        'Uttarakhand': ['Dehradun', 'Hardwar',
                        'Haldwani-cum-Kathgodam',
                        'Srinagar', 'Kashipur', 'Roorkee', 'Rudrapur',
                        'Rishikesh',
                        'Ramnagar', 'Pithoragarh', 'Manglaur',
                        'Nainital',
                        'Mussoorie', 'Tehri', 'Pauri', 'Nagla',
                        'Sitarganj',
                        'Bageshwar'],
        'Puducherry': ['Pondicherry', 'Karaikal',
                       'Yanam', 'Mahe'],
        'Tripura': ['Agartala', 'Udaipur',
                    'Dharmanagar', 'Pratapgarh',
                    'Kailasahar', 'Belonia', 'Khowai'],
        'Mizoram': ['Aizawl', 'Lunglei', 'Saiha'],
        'Meghalaya': ['Shillong', 'Tura',
                      'Nongstoin'],
        'Manipur': ['Imphal', 'Thoubal', 'Lilong',
                    'Mayang Imphal'],
        'Himachal Pradesh': ['Shimla', 'Mandi',
                             'Solan', 'Nahan', 'Sundarnagar',
                             'Palampur'],
        'Nagaland': ['Dimapur', 'Kohima', 'Zunheboto',
                     'Tuensang', 'Wokha',
                     'Mokokchung'],
        'Goa': ['Marmagao', 'Panaji', 'Margao',
                'Mapusa'],
        'Arunachal Pradesh': ['Naharlagun',
                              'Pasighat'],
        'Dadra and Nagar Haveli': ['Silvassa'],
        'Maharashtra': ['Ahmadnagar (Ahmednagar)',
                        'Akola',
                        'Amravati',
                        'Aurangabad',
                        'Bhandara',
                        'Bid (Beed)',
                        'Buldana (Buldhana)',
                        'Chandrapur',
                        'Dhule',
                        'Gadchiroli',
                        'Gondiya (Gondia)',
                        'Hingoli',
                        'Jalgaon',
                        'Jalna',
                        'Kolhapur',
                        'Latur',
                        'Mumbai',
                        'Mumbai Suburban',
                        'Nagpur',
                        'Nanded',
                        'Nandurbar',
                        'Nashik',
                        'Osmanabad',
                        'Parbhani',
                        'Pune',
                        'Raigad',
                        'Ratnagiri',
                        'Sangli',
                        'Satara',
                        'Sindhudurg',
                        'Solapur',
                        'Thane',
                        'Wardha',
                        'Washim',
                        'Yavatmal'
                        ]
    }
    s = State.objects.all()
    c = City.objects.all()
    s.delete()
    c.delete()
    #
    state_rec = []
    city_rec = []
    for k, v in STATE_N_CITY.items():
        state_rec.append({
            'name': k
        })
        # s = State.objects.create(name=k)
        # s.save()
        for cty in v:
            city_rec.append(
                {
                    'name': cty,
                    'state': s
                }
            )
            # try:
            #     c = City.objects.create(state=s)
            #     c.name = cty
            #     c.save()
            # except IntegrityError:
            #     continue
    State.objects.bulk_create([State(**q) for q in state_rec])
    City.objects.bulk_create([City(**q) for q in city_rec])
    print('done')


def add_category():
    from api import GLOBAL
    c = Category.objects.all()
    c.delete()
    rec = []
    for a, b in GLOBAL.CATEGORIES:
        rec.append(
            {'name': b.strip()}
        )
    Category.objects.bulk_create([Category(**q) for q in rec])
    print('done...')


class HelloView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        content = {'message': 'Hello, %s!' % request.user}
        # add_category()
        # x = send_mail(subject='Hello API from VepoLink',
        #               message='',
        #               from_email='VepoLink',
        #               recipient_list=['incompletesagar@gmail.com'],
        #               )
        # print(x)

        return Response(content)


class RegistrationViewSet(viewsets.GenericViewSet):
    # settings permission_classes empty will open this API
    permission_classes = []
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer


def ReadingView(request):
    message = []
    pk = request.GET.get('pk')
    # date format 200213122657 => strptime '%y%m%d%H%M%S'
    from_dt = request.GET.get('from_dt')
    to_dt = request.GET.get('to_dt')
    if from_dt and to_dt:
        from_dt = datetime.strptime(from_dt, '%y%m%d%H%M%S')
        to_dt = datetime.strptime(to_dt, '%y%m%d%H%M%S')
    else:
        from_dt = datetime.now() - timedelta(hours=48)
        to_dt = datetime.now()
    try:
        station = Station.objects.get(uuid=pk)
        qs = Reading.objects.filter(station=station,
                                    # reading__ph__gte=5,
                                    reading__timestamp__gte=from_dt,
                                    reading__timestamp__lte=to_dt,
                                    )
        if not qs:
            message.append({'error': 'No records for the selected range'})
        qs = qs.select_related('station')
        qs = qs.values_list('reading', flat=True)
        qs = dict(
            name=station.name,
            prefix=station.prefix,
            status='success',
            start=from_dt,
            end=to_dt,
            count=len(qs),
            message=message,
            readings=list(qs)
        )
        # df=pd.DataFrame(qs)
        # print(df.to_json())
        # serializer_class = ReadingSerializer(queryset)
        return JsonResponse(qs, status=status.HTTP_200_OK)
    except Station.DoesNotExist:
        return HttpResponseBadRequest('Station missing')
