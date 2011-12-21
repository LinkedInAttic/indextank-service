from updates import updates
from django.db.models import signals
from models import create_package, create_analyzer, create_provisioner, AnalyzerComponent, DataSet

def update_database(app, created_models, verbosity, **kwargs):
    updates.perform_updates()

signals.post_syncdb.connect(update_database)

def populate_packages(app, created_models, verbosity, **kwargs):
    
#                                  snippets=index.allows_snippets, 
#                                  facets=index.allows_faceting, 
#                                  facets_bits=index.facets_bits,
#                                  autocomplete=index.allows_autocomplete,
#                                  autocomplete_type=index.autocomplete_type,
#                                  variables=index.max_variables, 
#                                  rti_size=index.rti_documents_number,
#                                  xmx=index.max_memory_mb)
#    

    default_config = {'allows_snippets': True, 
                      'allows_facets': True,
                      'facets_bits': 5,
                      'autocomplete': True, 
                      'autocomplete_type': 'documents',
                      'max_variables': 3,
                      'rti_size': 500,
                      'xmx': 600, 
                      }
    def config(dct):
        cfg = default_config.copy()
        cfg.update(dct)
        return cfg

    ########################### CUSTOM PLANS #############################
    create_package(name='Formspring custom', code="FORMSPRING", base_price=0, index_max_size=5000000, searches_per_day=2000, max_indexes=1,
                   configuration_map=config({'allows_facets': False, 'rti_size': 10000, 'xmx': 13000}))
    create_package(name='Spoke custom', code="SPOKE", base_price=0, index_max_size=12000000, searches_per_day=2000, max_indexes=1,
                   configuration_map=config({'allows_facets': False, 'rti_size': 10000, 'xmx': 26000}))
    create_package(name='Reddit custom', code="REDDIT", base_price=0, index_max_size=5000000, searches_per_day=400000, max_indexes=4,
               configuration_map=config({ 'allow_snippets': False, 'allows_facets': False, 'autocomplete_type': 'queries', 'xmx': 13000, 'rti_size': 2500, 'vmargs': ['-DlimitTermBasedQueryMatcher=50000,1500'] }))

    ########################## FREE ########################## 
    create_package(name='Free', code="FREE", base_price=0, index_max_size=100000, searches_per_day=500, max_indexes=5,
                  configuration_map=config({'allows_facets': True, 'xmx': 700}))

    ########################## PAID PLANS ########################## 
    create_package(name='Plus', code="PLUS_TANK", base_price=49, index_max_size=500000, searches_per_day=1000, max_indexes=5,
                   configuration_map=config({'allows_facets': True, 'xmx': 750, 'storage': 'bdb', 'bdb_cache': 50}))
    create_package(name='Premium', code="PREMIUM_TANK", base_price=98, index_max_size=1000000, searches_per_day=1000, max_indexes=5,
                   configuration_map=config({'allows_facets': True, 'xmx': 1200, 'storage': 'bdb', 'bdb_cache': 150}))
    create_package(name='Pro', code="PRO_TANK", base_price=175, index_max_size=2000000, searches_per_day=1000, max_indexes=5,
                   configuration_map=config({'allows_facets': True, 'xmx': 2048, 'storage': 'bdb', 'bdb_cache': 300, 'rti_size': 10000}))
    
    ########################## INCUBATOR PLANS ########################## 
    create_package(name='YCombinator 90 days free', code="YCOMBINATOR_90DAYS", base_price=0, index_max_size=2000000, searches_per_day=1000, max_indexes=5,
                   configuration_map=config({'allows_facets': True, 'xmx': 2048, 'storage': 'bdb', 'bdb_cache': 300, 'rti_size': 10000}))
    
    ########################## HEROKU PLANS ########################## 
    create_package(name='Heroku Starter', code="HEROKU_STARTER", base_price=0, index_max_size=100000, searches_per_day=500, max_indexes=5,
                  configuration_map=config({'allows_facets': True, 'xmx': 700}))
    create_package(name='Heroku Plus', code="HEROKU_PLUS", base_price=49, index_max_size=500000, searches_per_day=1000, max_indexes=5,
                   configuration_map=config({'allows_facets': True, 'xmx': 750, 'storage': 'bdb', 'bdb_cache': 50}))
    create_package(name='Heroku Pro', code="HEROKU_PRO", base_price=175, index_max_size=2000000, searches_per_day=1000, max_indexes=5,
                   configuration_map=config({'allows_facets': True, 'xmx': 2048, 'storage': 'bdb', 'bdb_cache': 300, 'rti_size': 10000}))

    ########################## CONTEST PLANS ########################## 
    create_package(name='Heroku Contest', code="HEROKU_CONTEST_30DAY", base_price=0, index_max_size=1000000, searches_per_day=20000, max_indexes=5,
                   configuration_map=config({'max_variables': 5, 'xmx': 1500}))
    create_package(name='Factual Contest', code="FACTUAL_CONTEST_30DAY", base_price=0, index_max_size=1000000, searches_per_day=20000, max_indexes=5,
                   configuration_map=config({'max_variables': 5, 'xmx': 1500}))
    create_package(name='Crawlathon', code="80LEGS_CONTEST_30DAY", base_price=0, index_max_size=1000000, searches_per_day=20000, max_indexes=5,
                   configuration_map=config({'max_variables': 5, 'allows_facets': True, 'xmx': 1200, 'storage': 'bdb', 'bdb_cache': 150}))
    
def populate_datasets(app, created_models, verbosity, **kwargs):
    datasets = DataSet.objects.filter(code='DEMO').all()
    
    if len(datasets) == 0:
        dataset = DataSet()
        dataset.name = 'DEMO'
        dataset.code = 'DEMO'
        dataset.filename = 'inst.json'
        dataset.size = 440

        dataset.save()
    
def populate_analyzers(app, created_models, verbosity, **kwargs):
    create_analyzer(code='DEFAULT', name='Default IndexTank analyzer', config='{}', factory='com.flaptor.indextank.query.IndexEngineAnalyzer', type=AnalyzerComponent.Types.tokenizer, enabled=True)
    create_analyzer(code='ENG_STOPWORDS', name='Default IndexTank analyzer with english stopwords', config='{"stopwords":["a","about","above","after","again","against","all","am","an","and","any","are","aren\'t","as","at","be","because","been","before","being","below","between","both","but","by","can\'t","cannot","could","couldn\'t","did","didn\'t","do","does","doesn\'t","doing","don\'t","down","during","each","few","for","from","further","had","hadn\'t","has","hasn\'t","have","haven\'t","having","he","he\'d","he\'ll","he\'s","her","here","here\'s","hers","herself","him","himself","his","how","how\'s","i","i\'d","i\'ll","i\'m","i\'ve","if","in","into","is","isn\'t","it","it\'s","its","itself","let\'s","me","more","most","mustn\'t","my","myself","no","nor","not","of","off","on","once","only","or","other","ought","our","ours","     ourselves","out","over","own","same","shan\'t","she","she\'d","she\'ll","she\'s","should","shouldn\'t","so","some","such","than","that","that\'s","the","their","theirs","them","themselves","then","there","there\'s","these","they","they\'d","they\'ll","they\'re","they\'ve","this","those","through","to","too","under","until","up","very","was","wasn\'t","we","we\'d","we\'ll","we\'re","we\'ve","were","weren\'t","what","what\'s","when","when\'s","where","where\'s","which","while","who","who\'s","whom","why","why\'s","with","won\'t","would","wouldn\'t","you","you\'d","you\'ll","you\'re","you\'ve","your","yours","yourself","yourselves"]}', factory='com.flaptor.indextank.query.IndexEngineAnalyzer', type=AnalyzerComponent.Types.tokenizer, enabled=True)
    create_analyzer(code='ENGLISH_STEMMER', name='English Stemmer filter', config='{"stemmerName":"English"}', factory='com.flaptor.indextank.query.analyzers.StemmerFilter', type=AnalyzerComponent.Types.filter, enabled=True)
    create_analyzer(code='CJK', name='CJK Analyzer', config='{"match_version":"29"}', factory='com.flaptor.indextank.query.IndexEngineCJKAnalyzer', type=AnalyzerComponent.Types.tokenizer, enabled=True)
    
    
signals.post_syncdb.connect(populate_packages)
signals.post_syncdb.connect(populate_analyzers)
signals.post_syncdb.connect(populate_datasets)
