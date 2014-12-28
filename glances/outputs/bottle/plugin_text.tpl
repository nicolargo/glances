% if stats['msgdict'] != []:
<section id="{{ plugin_name }}" class="plugin">
% for msg in stats['msgdict']:
    % if stats['display']:
    <span class="{{ msg['decoration'].lower() }} {{ 'hidden-xs hidden-sm' if msg['optional'] else '' }}">
        {{ msg['msg'] }}
    </span>
    % end
% end
</section>
% end