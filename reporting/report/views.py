"""
    Report views
    
    @author: M. Doucet, Oak Ridge National Laboratory
    @copyright: 2014-2015 Oak Ridge National Laboratory
"""
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.utils import dateformat, timezone
from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.vary import vary_on_cookie
from django.conf import settings
from django.contrib.auth.decorators import login_required
import logging
import sys
import os
import json

from report.models import DataRun, IPTS, Instrument, Error, RunStatus
from dasmon.models import ActiveInstrument
from icat_server_communication import get_run_info
import datetime
import view_util
import users.view_util
import dasmon.view_util
import reporting_app.view_util
from forms import ProcessingForm

@login_required
def processing_admin(request):
    """
        Form to let admins easily reprocess parts of the workflow
    """
    breadcrumbs = "<a href='%s'>home</a> &rsaquo; processing" % reverse(settings.LANDING_VIEW)
    template_values = {'breadcrumbs':breadcrumbs, 'notes': ''}
    template_values = users.view_util.fill_template_values(request, **template_values)

    if request.method == 'POST':
        # Get instrument
        if 'instrument' in request.POST:
            instrument = request.POST['instrument']
            
        processing_form = ProcessingForm(request.POST)
        if processing_form.is_valid():
            output = processing_form.process()
            template_values['notes'] = output['report']
            
            # Submit task and append success outcome to notes.
            if 'runs' in output and 'instrument' in output \
                and 'task' in output and output['task'] is not None:
                submission_errors = ""
                for run_obj in output['runs']:
                    try:
                        view_util.send_processing_request(output['instrument'], run_obj, 
                                                          user=request.user, destination=output['task'])
                    except:
                        submission_errors += "%s run %s could not be submitted: %s<br>" % \
                            (str(run_obj.instrument_id), str(run_obj.run_number), sys.exc_value)
                        logging.error(sys.exc_value)
                template_values['notes'] += submission_errors
                if len(submission_errors) == 0:
                    template_values['notes'] += "<b>All tasks were submitted</b><br>"
    else:
        # Get instrument
        if 'instrument' in request.GET:
            instrument = request.GET['instrument']
        else:
            instruments = [ str(i) for i in Instrument.objects.all().order_by('name') if ActiveInstrument.objects.is_alive(i) ]
            instrument = instruments[0]
            
        processing_form = ProcessingForm()
        processing_form.set_initial(request.GET)

    # Get list of available experiments
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())
    ipts = [ str(i) for i in IPTS.objects.filter(instruments=instrument_id) ]

    template_values['form'] = processing_form
    template_values['experiment_list'] = ipts
    template_values.update(csrf(request))

    return render_to_response('report/processing_admin.html',
                              template_values)


@users.view_util.login_or_local_required
def summary(request):
    """
        List of available instruments
    """
    instruments = Instrument.objects.all().order_by('name')
    # Get base URL
    base_url = reverse('report.views.instrument_summary', args=['aaaa'])
    base_url = base_url.replace('/aaaa', '')
    breadcrumbs = "<a href='%s'>home</a> &rsaquo; summary" % reverse(settings.LANDING_VIEW)

    # Number of runs as a function of time
    max_date = datetime.datetime.now().replace(day=1).replace(tzinfo=timezone.get_current_timezone())
    epoch = datetime.datetime(1970, 1, 1).replace(tzinfo=timezone.get_current_timezone())
    adara_start = datetime.datetime(2012, 10, 1).replace(tzinfo=timezone.get_current_timezone())
    today = datetime.datetime.today().replace(tzinfo=timezone.get_current_timezone())
    # Fill in the partial data for the current month
    runs = DataRun.objects.filter(created_on__gte=max_date)
    run_rate = []
    run_summary = [{'min_date': max_date,
                    'max_date': datetime.datetime.today(),
                    'number_of_runs': len(runs)}]
    run_rate.append([1000 * int((today - epoch).total_seconds()), len(runs)])
    while True:
        # Make sure we don't display zeros for the period before
        # the system was installed
        if max_date < adara_start:
            break
        # Start date
        month = max_date.month - 1
        if month <= 0:
            min_date = max_date.replace(month=12, year=max_date.year - 1)
        else:
            min_date = max_date.replace(month=month)

        runs = DataRun.objects.filter(created_on__lt=max_date,
                                      created_on__gte=min_date)
        run_summary.append({'min_date': min_date,
                            'max_date': max_date,
                            'number_of_runs': len(runs)})
        run_rate.append([1000 * int((max_date - epoch).total_seconds()), len(runs)])

        # Update end date
        month = max_date.month - 1
        if month <= 0:
            max_date = max_date.replace(month=12, year=max_date.year - 1)
        else:
            max_date = max_date.replace(month=month)

    template_values = {'instruments':instruments,
                       'run_summary': run_summary,
                       'run_rate': run_rate,
                       'breadcrumbs':breadcrumbs,
                       'base_instrument_url':base_url}
    template_values = users.view_util.fill_template_values(request, **template_values)
    return render_to_response('report/global_summary.html',
                              template_values)

@users.view_util.login_or_local_required
@users.view_util.monitor
def detail(request, instrument, run_id):
    """
        Run details
        @param instrument: instrument name
        @param run_id: run number, as string
    """
    # Get instrument
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())
    run_object = get_object_or_404(DataRun, instrument_id=instrument_id, run_number=run_id)

    icat_info = get_run_info(instrument, str(run_object.ipts_id), run_id)

    # Breadcrumbs
    breadcrumbs = "<a href='%s'>home</a>" % reverse(settings.LANDING_VIEW)
    breadcrumbs += " &rsaquo; <a href='%s'>%s</a>" % (reverse('report.views.instrument_summary',
                                                              args=[instrument]), instrument)
    breadcrumbs += " &rsaquo; <a href='%s'>%s</a>" % (reverse('report.views.ipts_summary',
                                                              args=[instrument, run_object.ipts_id.expt_name]),
                                                      str(run_object.ipts_id).lower())
    breadcrumbs += " &rsaquo; run %s" % run_id
    if users.view_util.is_experiment_member(request, instrument_id, run_object.ipts_id) is False:
        template_values = {'instrument':instrument.upper(),
                           'run_object':run_object,
                           'helpline': settings.HELPLINE_EMAIL,
                           'breadcrumbs':breadcrumbs}
        template_values = users.view_util.fill_template_values(request, **template_values)
        template_values = dasmon.view_util.fill_template_values(request, **template_values)
        return render_to_response('report/private_data.html', template_values)

    # Check whether we need a re-reduce link
    reduce_url = None
    if view_util.needs_reduction(request, run_object):
        reduce_url = 'reduce'

    # Find status entries
    status_objects = RunStatus.objects.filter(run_id=run_object).order_by('created_on').reverse()

    # Look for an image of the reduction
    image_url = None
    try:
        from file_handling.models import ReducedImage
        images = ReducedImage.objects.filter(run_id=run_object)
        if len(images) > 0:
            image = images.latest('created_on')
            if image is not None and bool(image.file) and os.path.isfile(image.file.path):
                image_url = image.file.url
    except:
        logging.error("Error finding reduced image: %s" % sys.exc_value)

    # Look for an image of the reduction
    json_data = None
    plot_data = None
    x_label = "Q [1/\u00C5]"
    y_label = "Absolute reflectivity"
    try:
        from file_handling.models import JsonData
        json_data_list = JsonData.objects.filter(run_id=run_object)
        if len(json_data_list) > 0:
            json_data_entry = json_data_list.latest('created_on')
            if json_data_entry is not None :
                json_data = json_data_entry.data
                data_dict = json.loads(json_data)
                if 'main_output' in data_dict:
                    # Old format
                    if 'x' in data_dict['main_output']:
                        x_values = data_dict['main_output']['x']
                        y_values = data_dict['main_output']['y']
                        e_values = data_dict['main_output']['e']
                        if 'x_label' in data_dict['main_output']:
                            x_label = data_dict['main_output']['x_label']
                        if 'y_label' in data_dict['main_output']:
                            y_label = data_dict['main_output']['y_label']
                        plot_data = [[x_values[i], y_values[i], e_values[i]] for i in range(len(y_values))]
                    # New format from Mantid
                    elif 'data' in data_dict['main_output']:
                        x_values = data_dict['main_output']['data']['1'][0]
                        y_values = data_dict['main_output']['data']['1'][1]
                        e_values = data_dict['main_output']['data']['1'][2]
                        if 'axes' in data_dict['main_output']:
                            if 'xlabel' in data_dict['main_output']['axes']:
                                x_label = data_dict['main_output']['axes']['xlabel']
                            if 'ylabel' in data_dict['main_output']['axes']:
                                y_label = data_dict['main_output']['axes']['ylabel']
                        if len(data_dict['main_output']['data']['1'])>3:
                            dx = data_dict['main_output']['data']['1'][3]
                            plot_data = [[x_values[i], y_values[i], e_values[i], dx[i]] for i in range(len(y_values))]
                        else:
                            plot_data = [[x_values[i], y_values[i], e_values[i]] for i in range(len(y_values))]
        elif not request.GET.get('test', '-1') == '-1':
            plot_data = [[0.008, 0.0048], [0.0082, 0.96], [0.0084, 1], [0.0085, 1.1], [0.0087, 1],
                         [0.0089, 0.96], [0.0091, 1], [0.0092, 1], [0.0094, 1], [0.0096, 0.96],
                         [0.0098, 0.98], [ 0.01, 0.99], [ 0.01, 1.1], [ 0.01, 0.96], [0.011, 0.9],
                         [0.011, 0.82], [0.011, 0.69], [0.011, 0.64], [0.011, 0.48], [0.012, 0.37],
                         [0.012, 0.25], [0.012, 0.14], [0.013, 0.1], [0.013,  0.1], [0.013, 0.14],
                         [0.013, 0.15], [0.014, 0.16], [0.014, 0.2], [0.014,  0.2], [0.015, 0.22],
                         [0.015, 0.22], [0.015, 0.19], [0.015, 0.2], [0.016, 0.17], [0.016, 0.16],
                         [0.016, 0.13], [0.017, 0.1], [0.017, 0.072], [0.018, 0.054], [0.018, 0.041],
                         [0.018, 0.027], [0.019, 0.025], [0.019, 0.02], [0.02, 0.026], [0.02, 0.03]]
    except:
        logging.error("Error finding reduced json data: %s" % sys.exc_value)

    # Check whether this is the last known run for this instrument
    last_run_id = DataRun.objects.get_last_cached_run(instrument_id)
    if last_run_id == run_object:
        next_url = None
    else:
        try:
            DataRun.objects.get(instrument_id=instrument_id,
                                run_number=run_object.run_number + 1)
            next_url = reverse('report.views.detail', args=[instrument, run_object.run_number + 1])
        except:
            next_url = None

    # Get previous run
    try:
        DataRun.objects.get(instrument_id=instrument_id,
                            run_number=run_object.run_number - 1)
        prev_url = reverse('report.views.detail', args=[instrument, run_object.run_number - 1])
    except:
        prev_url = None

    is_test_2d = 'test2d' in request.GET
    if is_test_2d:
        plot_data = None
    template_values = {'instrument':instrument.upper(),
                       'run_object':run_object,
                       'status':status_objects,
                       'breadcrumbs':breadcrumbs,
                       'icat_info':icat_info,
                       'reduce_url':reduce_url,
                       'plot_data':plot_data,
                       'plot_label_x':x_label,
                       'plot_label_y':y_label,
                       'reduction_setup_url':reporting_app.view_util.reduction_setup_url(instrument),
                       'image_url':image_url,
                       'prev_url': prev_url,
                       'next_url': next_url,
                       'test2d': is_test_2d,
                      }
    if icat_info == {}:
        template_values['user_alert'] = ["Could not communicate with ICAT: please notify ICAT support staff"]
    try:
        if 'data_files' not in icat_info or icat_info['data_files'] is None or len(icat_info['data_files'])==0:
            template_values['no_icat_info'] = True
    except:
        logging.error("Could not determine whether we have ICAT info: %s" % sys.exc_value)
        template_values['no_icat_info'] = True
    template_values = users.view_util.fill_template_values(request, **template_values)
    template_values = dasmon.view_util.fill_template_values(request, **template_values)
    return render_to_response('report/detail.html', template_values)

@login_required
@users.view_util.monitor
def submit_for_reduction(request, instrument, run_id):
    """
        Send a run for automated reduction
        @param instrument: instrument name
        @param run_id: run number
    """
    return view_util.processing_request(request, instrument, run_id,
                                        destination='/queue/REDUCTION.REQUEST')

@login_required
@users.view_util.monitor
def submit_for_post_processing(request, instrument, run_id):
    """
        Send a run for complete post-processing
        @param instrument: instrument name
        @param run_id: run number
    """
    return view_util.processing_request(request, instrument, run_id,
                                        destination='/queue/POSTPROCESS.DATA_READY')

@login_required
@users.view_util.monitor
def submit_for_cataloging(request, instrument, run_id):
    """
        Send a run for cataloging
        @param instrument: instrument name
        @param run_id: run number
    """
    return view_util.processing_request(request, instrument, run_id,
                                        destination='/queue/CATALOG.REQUEST')

@users.view_util.login_or_local_required
@users.view_util.monitor
def instrument_summary(request, instrument):
    """
        Instrument summary page
        @param instrument: instrument name
    """
    # Get instrument
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())

    # Get list of IPTS
    ipts = IPTS.objects.filter(instruments=instrument_id).order_by('created_on').reverse()
    expt_list = []
    for expt in ipts:
        localtime = timezone.localtime(expt.created_on)
        df = dateformat.DateFormat(localtime)
        expt_list.append({'experiment': str("<a href='%s'>%s</a>" % (reverse('report.views.ipts_summary',
                                                                             args=[instrument, expt.expt_name]),
                                                                     expt.expt_name)),
                          'total': expt.number_of_runs(),
                          'timestamp': expt.created_on.isoformat(),
                          'created_on': str(df.format(settings.DATETIME_FORMAT))})

    # Instrument error URL
    error_url = reverse('report.views.live_errors', args=[instrument])

    # Update URL for live monitoring
    update_url = reverse('report.views.get_instrument_update', args=[instrument])

    # Get the last IPTS created so that we can properly do the live update
    if IPTS.objects.filter(instruments=instrument_id).count() > 0:
        last_expt_created = IPTS.objects.filter(instruments=instrument_id).latest('id')
    else:
        last_expt_created = None

    # Breadcrumbs
    breadcrumbs = "<a href='%s'>home</a> &rsaquo; %s" % (reverse(settings.LANDING_VIEW),
                                                         instrument.lower())

    template_values = {'instrument':instrument.upper(),
                       'expt_list': expt_list,
                       'breadcrumbs':breadcrumbs,
                       'error_url': error_url,
                       'update_url':update_url,
                       'last_expt_created':last_expt_created,
                      }
    template_values = view_util.fill_template_values(request, **template_values)
    template_values = users.view_util.fill_template_values(request, **template_values)
    return render_to_response('report/instrument.html', template_values)

@users.view_util.login_or_local_required
@users.view_util.monitor
def ipts_summary(request, instrument, ipts):
    """
        Experiment summary giving the list of runs
        @param instrument: instrument name
        @param ipts: experiment name
    """
    # Protect against lower-case requests
    ipts = ipts.upper()
    # Get instrument
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())
    # Get experiment
    ipts_id = get_object_or_404(IPTS, expt_name=ipts, instruments=instrument_id)

    # Get IPTS URL
    ipts_url = reverse('report.views.ipts_summary', args=[instrument, ipts])
    update_url = reverse('report.views.get_experiment_update', args=[instrument, ipts])

    # Get the latest run and experiment so we can determine later
    # whether the user should refresh the page
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())

    runs = DataRun.objects.filter(instrument_id=instrument_id,
                                  ipts_id=ipts_id).order_by('created_on')
    run_list = view_util.get_run_list_dict(runs)

    # Get the ID of the first displayed run so that we can update the
    # status of runs that are displayed
    first_run_id = 0
    if len(runs) > 0:
        first_run_id = runs[0].id

    # Breadcrumbs
    breadcrumbs = "<a href='%s'>home</a>" % reverse(settings.LANDING_VIEW)
    breadcrumbs += " &rsaquo; <a href='%s'>%s</a>" % (reverse('report.views.instrument_summary',
                                                              args=[instrument]), instrument)
    breadcrumbs += " &rsaquo; %s" % str(ipts_id).lower()

    template_values = {'instrument': instrument.upper(),
                       'ipts_number': ipts,
                       'run_list': run_list,
                       'breadcrumbs': breadcrumbs,
                       'ipts_url': ipts_url,
                       'update_url': update_url,
                       'first_run_id': first_run_id,
                      }
    template_values = view_util.fill_template_values(request, **template_values)
    template_values = users.view_util.fill_template_values(request, **template_values)
    return render_to_response('report/ipts_summary.html', template_values)

@users.view_util.login_or_local_required
@cache_page(settings.SLOW_PAGE_CACHE_TIMEOUT)
@cache_control(private=True)
@users.view_util.monitor
@vary_on_cookie
def live_errors(request, instrument):
    """
        Display the list of latest errors
    """
    # Get instrument
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())

    #TODO: let the user pick the timeframe for the errors.
    # Pick 30 days for now.
    time_period = 30
    delta_time = datetime.timedelta(days=time_period)
    oldest_time = timezone.now() - delta_time
    error_query = Error.objects.filter(run_status_id__created_on__gte=oldest_time,
                                       run_status_id__run_id__instrument_id=instrument_id).order_by('id')
    last_error_id = 0
    if len(error_query) > 0:
        last_error_id = error_query[len(error_query) - 1].id
    error_list = []
    for err in error_query:
        localtime = timezone.localtime(err.run_status_id.created_on)
        df = dateformat.DateFormat(localtime)
        error_list.append({'experiment': str("<a href='%s'>%s</a>" % (reverse('report.views.ipts_summary',
                                                                              args=[instrument,
                                                                                    err.run_status_id.run_id.ipts_id.expt_name]),
                                                                      err.run_status_id.run_id.ipts_id.expt_name)),
                           'run': str("<a href='%s'>%s</a>" % (reverse('report.views.detail',
                                                                       args=[instrument,
                                                                             err.run_status_id.run_id.run_number]),
                                                               err.run_status_id.run_id.run_number)),
                           'info': str(err.description),
                           'timestamp': err.run_status_id.created_on.isoformat(),
                           'created_on': str(df.format(settings.DATETIME_FORMAT))})

    # Instrument reporting URL
    instrument_url = reverse('report.views.instrument_summary', args=[instrument])
    update_url = reverse('report.views.get_error_update', args=[instrument])

    # Breadcrumbs
    breadcrumbs = "<a href='%s'>home</a>" % reverse(settings.LANDING_VIEW)
    breadcrumbs += " &rsaquo; <a href='%s'>%s</a>" % (reverse('report.views.instrument_summary',
                                                              args=[instrument]), instrument)
    breadcrumbs += " &rsaquo; errors"

    template_values = {'instrument':instrument.upper(),
                       'error_list':error_list,
                       'last_error_id': last_error_id,
                       'breadcrumbs':breadcrumbs,
                       'instrument_url':instrument_url,
                       'update_url':update_url,
                       'time_period':time_period
                      }
    template_values = view_util.fill_template_values(request, **template_values)
    template_values = users.view_util.fill_template_values(request, **template_values)
    return render_to_response('report/live_errors.html', template_values)

@users.view_util.login_or_local_required_401
@cache_page(settings.FAST_PAGE_CACHE_TIMEOUT)
def get_experiment_update(request, instrument, ipts):
    """
         Ajax call to get updates behind the scenes
         @param instrument: instrument name
         @param ipts: experiment name
    """
    # Get instrument
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())
    # Get experiment
    ipts_id = get_object_or_404(IPTS, expt_name=ipts, instruments=instrument_id)

    # Get last experiment and last run
    data_dict = view_util.get_current_status(instrument_id)
    data_dict = dasmon.view_util.get_live_runs_update(request, instrument_id, ipts_id, **data_dict)

    response = HttpResponse(json.dumps(data_dict), content_type="application/json")
    response['Connection'] = 'close'
    return response


@users.view_util.login_or_local_required_401
@cache_page(settings.FAST_PAGE_CACHE_TIMEOUT)
def get_instrument_update(request, instrument):
    """
         Ajax call to get updates behind the scenes
         @param instrument: instrument name
    """
    since = request.GET.get('since', '0')
    try:
        since = int(since)
        since_expt_id = get_object_or_404(IPTS, id=since)
    except:
        since = 0
        since_expt_id = None

    # Get the instrument
    instrument_id = get_object_or_404(Instrument, name=instrument.lower())

    # Get last experiment and last run
    data_dict = view_util.get_current_status(instrument_id)
    expt_list = IPTS.objects.filter(instruments=instrument_id, id__gt=since).order_by('created_on')

    update_list = []
    if since_expt_id is not None and len(expt_list) > 0:
        data_dict['last_expt_id'] = expt_list[0].id
        for e in expt_list:
            if since_expt_id.created_on < e.created_on:
                localtime = timezone.localtime(e.created_on)
                df = dateformat.DateFormat(localtime)
                expt_dict = {"ipts":e.expt_name.upper(),
                             "n_runs":e.number_of_runs(),
                             "created_on":df.format(settings.DATETIME_FORMAT),
                             "timestamp": e.created_on.isoformat(),
                             "ipts_id":e.id,
                            }
                update_list.append(expt_dict)
    data_dict['expt_list'] = update_list
    data_dict['refresh_needed'] = '1' if len(update_list) > 0 else '0'

    response = HttpResponse(json.dumps(data_dict), content_type="application/json")
    response['Connection'] = 'close'
    return response


@users.view_util.login_or_local_required_401
@cache_page(settings.FAST_PAGE_CACHE_TIMEOUT)
def get_error_update(request, instrument):
    """
         Ajax call to get updates behind the scenes
         @param instrument: instrument name
         @param ipts: experiment name
    """
    since = request.GET.get('since', '0')
    try:
        since = int(since)
        last_error_id = get_object_or_404(Error, id=since)
    except:
        last_error_id = None

    instrument_id = get_object_or_404(Instrument, name=instrument.lower())

    # Get last experiment and last run
    data_dict = view_util.get_current_status(instrument_id)

    err_list = []
    if last_error_id is not None:
        errors = Error.objects.filter(run_status_id__run_id__instrument_id=instrument_id,
                                      id__gt=last_error_id.id).order_by('run_status_id__created_on')
        if len(errors) > 0:
            last_error_id_number = None
            for e in errors:
                if last_error_id_number is None:
                    last_error_id_number = e.id

                if last_error_id.run_status_id.created_on < e.run_status_id.created_on:
                    localtime = timezone.localtime(e.run_status_id.created_on)
                    df = dateformat.DateFormat(localtime)
                    err_dict = {"run":e.run_status_id.run_id.run_number,
                                "ipts":e.run_status_id.run_id.ipts_id.expt_name,
                                "description":e.description,
                                "created_on":df.format(settings.DATETIME_FORMAT),
                                "timestamp":e.run_status_id.created_on.isoformat(),
                                "error_id":e.id,
                               }
                    err_list.append(err_dict)
            data_dict['last_error_id'] = last_error_id_number
    data_dict['errors'] = err_list
    data_dict['refresh_needed'] = '1' if len(err_list) > 0 else '0'

    response = HttpResponse(json.dumps(data_dict), content_type="application/json")
    response['Connection'] = 'close'
    return response


