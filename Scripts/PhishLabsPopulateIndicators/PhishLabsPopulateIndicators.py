import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
from distutils.util import strtobool

since = demisto.args().get('since')
delete_false_positive = bool(strtobool(demisto.args().get('delete_false_positive', 'false')))
limit = demisto.args().get('limit')
indicator_type = demisto.args().get('indicator_type')
command_args = {}

if since:
    command_args['since'] = since
if limit:
    command_args['limit'] = int(limit)
if indicator_type:
    command_args['indicator_type'] = indicator_type
if delete_false_positive:
    command_args['false_positive'] = 'true'

entry = demisto.executeCommand('phishlabs-global-feed', command_args)[0]

if isError(entry):
    return_error('Failed getting the global feed from phishlabs - {}'.format(entry['Contents']))

content = entry.get('Contents')
if not content or not isinstance(content, dict):
    return_error('No indicators found')

feed = content.get('data', [])

if delete_false_positive:
    false_positives = list(filter(lambda f: bool(strtobool(str(f.get('falsePositive')))) is True, feed))
    for false_positive in false_positives:
        delete_res = demisto.executeCommand('deleteIndicators',
                                            {'query': 'source:"PhishLabs" and value:"{}"'
                                                .format(false_positive.get('value')), 'doNotWhitelist': 'true'})
        if isError(delete_res[0]):
            return_error('Error deleting PhishLabs indicators - {}'.format(delete_res[0]['Contents']))
else:
    for indicator in feed:
        indicator_type = indicator.get('type')
        indicator_value = indicator.get('value')
        indicator_timestamp = None
        if indicator.get('createdAt'):
            indicator_timestamp = datetime.strptime(indicator['createdAt'], '%Y-%m-%dT%H:%M:%SZ')
        if indicator_type == 'Attachment':
            indicator_type = 'File MD5'
            file_md5_attribute = list(filter(lambda f: f.get('name') == 'md5', indicator.get('attributes', [])))
            indicator_value = file_md5_attribute[0].get('value') if file_md5_attribute else ''

        demisto_indicator = {
            'type': indicator_type,
            'value': indicator_value,
            'source': 'PhishLabs',
            'reputation': 'Bad',
            'seenNow': 'true',
            'comment': 'From PhishLabs Global Feed'
        }

        if indicator_timestamp:
            demisto_indicator['timestamp'] = datetime.strftime(indicator_timestamp, '%Y-%m-%dT%H:%M:%S')

        indicator_res = demisto.executeCommand('createNewIndicator', demisto_indicator)

        if isError(indicator_res[0]):
            return_error('Error creating indiciator - {}'.format(indicator_res[0]['Contents']))

demisto.results('Successfully populated indicators')
