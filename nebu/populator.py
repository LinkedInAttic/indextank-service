from lib.monitor import Monitor
from nebu.models import Index, IndexPopulation
from lib.indextank.client import ApiClient
from django.utils import simplejson as json

from lib import flaptor_logging

batch_size = 1000
dataset_files_path = './'

logger = flaptor_logging.get_logger('Populator')

class IndexPopulator(Monitor):
    
    def __init__(self):
        super(IndexPopulator, self).__init__()
        self.failure_threshold = 5
        self.fatal_failure_threshold = 20
        self.period = 30

    def iterable(self):
        return IndexPopulation.objects.exclude(status=IndexPopulation.Statuses.finished)
        
    def monitor(self, population):
        client = ApiClient(population.index.account.get_private_apiurl())
        index = client.get_index(population.index.name)
        
        if index.has_started():
            if population.status == IndexPopulation.Statuses.created:
                logger.info('Populating index ' + population.index.code + ' with dataset "' + population.dataset.name + '"')
    
                population.status = IndexPopulation.Statuses.populating
                population.populated_size = 0
                population.save()
                
            eof, documents_added = self._populate_batch(population.index, population.dataset, population.populated_size, batch_size)
            population.populated_size = population.populated_size + documents_added
            
            if eof:
                population.status = IndexPopulation.Statuses.finished
            
            population.save()
                
        return True

    '''
        line_from: zero based
    '''
    def _populate_batch(self, index, dataset, line_from, lines):
        logger.info('Adding batch from line ' + str(line_from))

        client = ApiClient(index.account.get_private_apiurl())
        index = client.get_index(index.name)
        
        try:
            dataset_file = open(dataset_files_path + dataset.filename, 'r')
            for i in range(line_from):
                dataset_file.readline()
        except Exception, e:
            logger.error('Failed processing dataset file: %s', e)
            return False, 0
        
        
        added_docs = 0
        eof = False
        
        for i in xrange(lines):
            try:
                line = dataset_file.readline()
            except Exception, e:
                logger.error('Failed processing dataset file: %s', e)
                return False, added_docs
            
            if not line:
                break
            
            try:
                document = json.loads(line)
                id = document['docid']
                del document['docid']
                
                fields = document['fields']
                variables = document.get('variables', {})
    
                added_docs += 1
                index.add_document(id, fields)
                
                categories = document.get('categories')
                if categories:
                    index.update_categories(id, categories)
            except Exception, e:
                logger.error('Failed processing dataset line: %s', e)
                return False, added_docs
        
        eof = not dataset_file.readline()
        
        logger.info('Added ' + str(added_docs) + ' lines')
        
        return eof, added_docs
    
    def alert_title(self, deploy):
        return ''
    
    def alert_msg(self, deploy):
        return ''

if __name__ == '__main__':
    IndexPopulator().start()
