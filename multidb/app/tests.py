from django.test import TestCase
from .models import *

# Create your tests here.
data_table_1 = Datasource.objects.using('snappyflow').get(id='eoUq7Z83w0')
print("Printing ")
print(data_table_1.datasource_name)

data_table_2 = DatasourceClone.objects.create(
    id=data_table_1.id,
    datasource_name=data_table_1.datasource_name,
    type=data_table_1.type,
    default_ds=data_table_1.default_ds
)
data_table_2.save(using='local')
