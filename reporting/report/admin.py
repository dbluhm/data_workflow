from report.models import DataRun, StatusQueue, RunStatus
from django.contrib import admin

class DataRunAdmin(admin.ModelAdmin):
    list_display = ('run_number', 'instrument', 'ipts_number')

class RunStatusAdmin(admin.ModelAdmin):
    list_display = ('run_id', 'queue_id')

admin.site.register(DataRun, DataRunAdmin)
admin.site.register(StatusQueue)
admin.site.register(RunStatus, RunStatusAdmin)
