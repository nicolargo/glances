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
                        <td class="{{ msg['decoration'].lower() }} {{ 'hidden-xs hidden-sm' if msg['optional'] else '' }}">
                            {{ msg['msg'] }}  
                        </td>
                    % end
                % end
            % end
            </tr>
        </tbody>
    </table>    
</section>
% end