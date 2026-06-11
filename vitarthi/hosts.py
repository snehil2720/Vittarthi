from django_hosts import patterns, host

host_patterns = patterns(
    '',
    
    host(r'www', 'vita.urls', name='www'),

    host(r'app', 'financial_advisor.urls', name='app'),

    host(r'', 'vita.urls', name='root'),
)