def column_exists(table, column):
    from django.db import connection, transaction
    from django.db.backends.mysql import introspection
    
    cursor = connection.cursor()
    desc = connection.introspection.get_table_description(cursor, table)
    for x in desc:
        if x[0] == column:
            return True
    return False

def get_column_type(table, column):
    from django.db import connection, transaction
    
    cursor = connection.cursor()
    cursor.execute('desc %s' % table)
    for r in cursor.cursor:
        if r[0] == column:
            return r[1]
    return None

def safe_add_column(table, column, sqlargs):
    if not column_exists(table, column):
        print 'SCHEMA UPDATE: Adding missing column: %s.%s %s' % (table, column, sqlargs)
        from django.db import connection, transaction
        cursor = connection.cursor()
        sql = 'ALTER TABLE `%s` ADD COLUMN `%s` %s' % (table, column, sqlargs)
        cursor.execute(sql)
        
def makeNullable(table, column, columnTypeStr):
    print 'SCHEMA UPDATE: changing column %s in table %s to nullable' % (column, table)
    from django.db import connection, transaction
    cursor = connection.cursor()
    sql = 'ALTER TABLE `%s` MODIFY COLUMN `%s` %s NULL;' % (table,column,columnTypeStr)
    cursor.execute(sql)
