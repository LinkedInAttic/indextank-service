from util import column_exists, safe_add_column, makeNullable, get_column_type

def perform_updates():
    enlarge_username()
    add_change_password()
    add_analyzer_config()
    add_account_default_analyzer()
    add_effective_bdb()
    update_custom_subscription()    
    add_public_api()
    add_account_provisioner()
    add_deploy_dying()
    enlarge_ccdigits()
    enlarge_function_storage()
    add_index_deleted()

def add_public_api():
    safe_add_column('storefront_index', 'public_api', 'TINYINT(1) NOT NULL DEFAULT 0')

def add_deploy_dying():
    safe_add_column('storefront_deploy', 'dying', 'TINYINT(1) NOT NULL DEFAULT 0')

def add_index_status():
    safe_add_column('storefront_index', 'status', 'varchar(50) NOT NULL')

def add_index_deleted():
    safe_add_column('storefront_index', 'deleted', 'TINYINT(1) NOT NULL DEFAULT 0')

def enlarge_username():
    username_type = get_column_type('auth_user', 'username')
    if username_type != 'varchar(100)':
        print 'SCHEMA UPDATE: Enlarging auth_user.username column length to varchar(100)'
        
        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `auth_user` MODIFY COLUMN `username` varchar(100) NOT NULL'
        cursor.execute(sql)

        transaction.commit_unless_managed()
    

def enlarge_ccdigits():
    username_type = get_column_type('storefront_accountpayinginformation', 'credit_card_last_digits')
    if username_type != 'varchar(4)':
        print 'SCHEMA UPDATE: Enlarging auth_user.username column length to varchar(100)'

        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `storefront_accountpayinginformation` MODIFY COLUMN `credit_card_last_digits` varchar(4)'
        cursor.execute(sql)

        transaction.commit_unless_managed()


def add_analyzer_config():
    safe_add_column('storefront_index', 'analyzer_config', 'TEXT NULL')

def update_custom_subscription():
    if not column_exists('storefront_accountpayinginformation', 'monthly_amount'):
        print 'SCHEMA UPDATE: Upgrading table: storefront_accountpayinginformation'

        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `storefront_accountpayinginformation` MODIFY `first_name` varchar(50) NULL'
        cursor.execute(sql)
        sql = 'ALTER TABLE `storefront_accountpayinginformation` MODIFY `last_name` varchar(50) NULL'
        cursor.execute(sql)
        sql = 'ALTER TABLE `storefront_accountpayinginformation` MODIFY `contact_email` varchar(255) NULL'
        cursor.execute(sql)
        sql = 'ALTER TABLE `storefront_accountpayinginformation` MODIFY `credit_card_last_digits` varchar(3) NULL'
        cursor.execute(sql)
        sql = 'ALTER TABLE `storefront_accountpayinginformation` ADD COLUMN `subscription_status` varchar(30) NULL'
        cursor.execute(sql)
        sql = 'ALTER TABLE `storefront_accountpayinginformation` ADD COLUMN `subscription_type` varchar(30) NULL'
        cursor.execute(sql)
        sql = 'ALTER TABLE `storefront_accountpayinginformation` ADD COLUMN `monthly_amount` integer NULL'
        cursor.execute(sql)
 
        transaction.commit_unless_managed()

def add_account_default_analyzer():
    if not column_exists('storefront_account', 'default_analyzer_id'):
        print 'SCHEMA UPDATE: Adding missing column: storefront_account.default_analyzer'
        
        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `storefront_account` ADD COLUMN `default_analyzer_id` integer NULL'
        cursor.execute(sql)

        sql = 'ALTER TABLE `storefront_account` ADD CONSTRAINT `default_analyzer_id_refs_id_44eb0c5b` FOREIGN KEY (`default_analyzer_id`) REFERENCES `storefront_analyzer` (`id`)'
        cursor.execute(sql)
        transaction.commit_unless_managed()

def add_change_password():
    if not column_exists('storefront_pfuser', 'change_password'):
        print 'SCHEMA UPDATE: Adding missing column: storefront_pfuser.change_password'
        
        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `storefront_pfuser` ADD COLUMN `change_password` tinyint NULL'
        cursor.execute(sql)

        print 'DATA UPDATE'
        sql = 'UPDATE storefront_pfuser set change_password=0'
        cursor.execute(sql)
        sql = 'ALTER TABLE `storefront_pfuser` MODIFY COLUMN `change_password` tinyint NOT NULL'
        cursor.execute(sql)
        transaction.commit_unless_managed()

def add_effective_bdb():
    if not column_exists('storefront_deploy', 'effective_bdb'):
        print 'SCHEMA UPDATE: Adding missing column: storefront_deploy.effective_bdb'

        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `storefront_deploy` ADD COLUMN `effective_bdb` integer NOT NULL DEFAULT 0'
        cursor.execute(sql)

        transaction.commit_unless_managed()

def add_account_provisioner():
    safe_add_column('storefront_account', 'provisioner_id', 'integer NULL')
    
def enlarge_function_storage():
    func_def_type = get_column_type('storefront_scorefunction', 'definition')
    if func_def_type != 'varchar(4096)':
        print 'SCHEMA UPDATE: Enlarging storefront_scorefunction.definition column length to varchar(4096)'

        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `storefront_scorefunction` MODIFY COLUMN `definition` varchar(4096) DEFAULT NULL;'
        cursor.execute(sql)

        transaction.commit_unless_managed()



#def add_tag_slug():
#    if not column_exists('core_tag', 'slug'):
#        print 'SCHEMA UPDATE: Adding missing column: core_tag.slug'
#        
#        from django.db import connection, transaction
#        cursor = connection.cursor()
#        sql = 'ALTER TABLE `core_tag` ADD COLUMN `slug` varchar(50) NULL'
#        cursor.execute(sql)
#
#        print 'DATA UPDATE: Normalizing core.Tag texts, and generating slugs.'
#        sql = 'SELECT `id`, `text` FROM `core_tag`'
#        cursor.execute(sql)
#        for row in cursor:
#            id = row[0]
#            text = row[1]
#            text = Tag.normalize(text)
#            slug = slughifi(text)
#            sql = 'UPDATE `core_tag` SET `text`=%s, `slug`=%s WHERE `id`=%s'  
#            cursor.execute(sql, (text, slug, id))
#        
#        sql = 'ALTER TABLE `core_tag` MODIFY COLUMN `slug` varchar(50) NOT NULL'
#        cursor.execute(sql)
#        transaction.commit_unless_managed()
