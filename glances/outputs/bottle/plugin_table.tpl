% if stats['msgdict'] != []:
<section id="{{ plugin_name }}" class="plugin">
    <table class="table">
        <tbody>
            <tr>
            % for msg in stats['msgdict']:
                % if msg['msg'].startswith('\n'):
                </tr>
                <tr>
                % else:
                    % if stats['display']:
                        % if plugin_name == 'processlist':
                            % if not msg['splittable'] or msg['splittable'] and msg['decoration'] == 'PROCESS':
                            <td class="{{ msg['decoration'].lower() }}">
                                {{ msg['msg'] }}
                            </td>
                            % end
                        % else:
                            <td class="{{ msg['decoration'].lower() }} {{ 'hidden-xs hidden-sm' if msg['optional'] else '' }}">
                                {{ msg['msg'] }}  
                            </td>
                        % end
                    % end
                % end
            % end
            </tr>
        </tbody>
    </table>    
</section>
% end