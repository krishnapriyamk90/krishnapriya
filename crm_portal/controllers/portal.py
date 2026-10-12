from odoo import http
from odoo.http import request


class CRMPortal(http.Controller):

    @http.route(
        '/my/crm',
        type='http',
        auth='user',
        website=True
    )
    def crm_dashboard(self, **kwargs):

        # ---------------------------------------------------------
        # RECORD VISIBILITY
        # ---------------------------------------------------------
        # Admins can see all CRM records.
        # Portal users can see only their own CRM records.
        # ---------------------------------------------------------

        if request.env.user.has_group('base.group_system'):

            lead_domain = [
                ('type', '=', 'lead'),
            ]

            opportunity_domain = [
                ('type', '=', 'opportunity'),
            ]

        else:

            partner = request.env.user.partner_id

            lead_domain = [
                ('type', '=', 'lead'),
                ('partner_id', '=', partner.id),
            ]

            opportunity_domain = [
                ('type', '=', 'opportunity'),
                ('partner_id', '=', partner.id),
            ]

        Lead = request.env['crm.lead']

        # ---------------------------------------------------------
        # KPI COUNTS
        # ---------------------------------------------------------

        lead_count = Lead.search_count(lead_domain)

        opportunity_count = Lead.search_count(opportunity_domain)

        won_count = Lead.search_count(
            lead_domain + [
                ('stage_id.is_won', '=', True),
            ]
        ) + Lead.search_count(
            opportunity_domain + [
                ('stage_id.is_won', '=', True),
            ]
        )

        # ---------------------------------------------------------
        # REVENUE
        # ---------------------------------------------------------

        opportunities = Lead.search(opportunity_domain)

        total_revenue = sum(
            opportunities.mapped('expected_revenue')
        )

        # ---------------------------------------------------------
        # RECENT LEADS
        # ---------------------------------------------------------

        recent_leads = Lead.search(
            lead_domain,
            order='create_date desc, id desc',
            limit=5
        )

        # ---------------------------------------------------------
        # RECENT OPPORTUNITIES
        # ---------------------------------------------------------

        recent_opportunities = Lead.search(
            opportunity_domain,
            order='create_date desc, id desc',
            limit=5
        )

        # ---------------------------------------------------------
        # PIPELINE
        # ---------------------------------------------------------

        stages = request.env['crm.stage'].search(
            [],
            order='sequence, id'
        )

        pipeline = []

        for stage in stages:

            count = Lead.search_count(
                opportunity_domain + [
                    ('stage_id', '=', stage.id),
                ]
            )

            pipeline.append({
                'stage': stage,
                'count': count,
            })

        max_pipeline_count = max(
            [item['count'] for item in pipeline],
            default=0,
        )

        if max_pipeline_count == 0:
            max_pipeline_count = 1

        # ---------------------------------------------------------
        # UPCOMING ACTIVITIES
        # ---------------------------------------------------------

        activity_lead_ids = Lead.search(
            lead_domain + [
                ('id', '!=', False),
            ]
        ).ids

        activity_opportunity_ids = Lead.search(
            opportunity_domain + [
                ('id', '!=', False),
            ]
        ).ids

        activity_lead_ids = list(
            set(activity_lead_ids + activity_opportunity_ids)
        )

        activities = request.env['mail.activity'].sudo().search(
            [
                ('res_model', '=', 'crm.lead'),
                ('res_id', 'in', activity_lead_ids),
            ],
            order='date_deadline asc, id asc',
            limit=5
        )

        # ---------------------------------------------------------
        # RENDER DASHBOARD
        # ---------------------------------------------------------

        return request.render(
            'crm_portal.crm_dashboard',
            {
                'lead_count': lead_count,
                'opportunity_count': opportunity_count,
                'won_count': won_count,
                'total_revenue': total_revenue,

                'recent_leads': recent_leads,
                'recent_opportunities': recent_opportunities,

                'pipeline': pipeline,
                'max_pipeline_count': max_pipeline_count,

                'activities': activities,
            }
        )