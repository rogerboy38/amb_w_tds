frappe.pages['amb-cost-dashboard'].on_page_load = function(w) {
  var page = frappe.ui.make_app_page({parent: w, title: 'AMB Cost & KPI Dashboard', single_column: true});
  var $b = $('<div style="padding:8px 0"></div>').appendTo($(w).find('.layout-main-section'));
  function dot(c,t,a,r){ if(!t||!c) return 'var(--gray-400)'; var v=Math.abs((c-t)/t*100); return v>=(r||999)?'var(--red-500)':(v>=(a||999)?'var(--orange-500)':'var(--green-500)'); }
  function n(v){ return (v||v===0)?Number(v).toLocaleString():'-'; }
  frappe.call({method:'amb_w_tds.dashboard_api.get_cost_dashboard', callback:function(res){
    var R=(res.message&&res.message.records)||[];
    var tf=R.reduce(function(s,x){return s+(x.factor_count||0);},0);
    var h='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:18px">';
    h+='<div style="background:var(--control-bg);border-radius:6px;padding:12px"><div style="font-size:12px;color:var(--text-muted)">Cost bases</div><div style="font-size:22px;font-weight:600">'+R.length+'</div></div>';
    h+='<div style="background:var(--control-bg);border-radius:6px;padding:12px"><div style="font-size:12px;color:var(--text-muted)">Cost factors</div><div style="font-size:22px;font-weight:600">'+tf+'</div></div></div>';
    h+='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px">';
    R.forEach(function(x){
      var c=dot(x.current_calculated_value,x.target_value,x.threshold_warning,x.threshold_critical);
      h+='<div style="border:1px solid var(--border-color);border-radius:8px;padding:14px;background:var(--card-bg)">';
      h+='<div style="display:flex;justify-content:space-between"><a href="/app/amb-kpi-factors/'+encodeURIComponent(x.name)+'" style="font-weight:600">'+frappe.utils.escape_html(x.goal||x.name)+'</a><span style="width:11px;height:11px;border-radius:50%;background:'+c+';margin-top:4px"></span></div>';
      h+='<div style="font-size:12px;color:var(--text-muted);margin:4px 0 10px">'+(x.kpi_type||'')+' / '+(x.year||'')+' / '+(x.values_currency||'')+' / '+x.factor_count+' factors</div>';
      h+='<div style="font-size:12px;color:var(--text-muted)">base <b style="color:var(--text-color)">'+n(x.base_value)+'</b> &nbsp; target <b style="color:var(--text-color)">'+n(x.target_value)+'</b> &nbsp; current <b style="color:var(--text-color)">'+n(x.current_calculated_value)+'</b></div></div>';
    });
    h+='</div><div style="margin-top:14px;font-size:12px;color:var(--text-muted)">Dots are grey until current/target are loaded; they turn green/amber/red on variance vs thresholds.</div>';
    $b.html(h);
  }});
};
