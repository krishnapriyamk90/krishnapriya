from odoo import http
from odoo.http import request


class CRMPortalActivity(http.Controller):

    # =========================================================
    # ACCESS / VISIBILITY
    # =========================================================

    def _activity_access_domain(self):
        """Admin can see all CRM activities.
        Portal users can see only activities linked to
        their own CRM leads/opportunities.
        """

        if request.env.user.has_group('base.group_system'):
            return [
                ('res_model', '=', 'crm.lead'),
            ]

        partner_id = request.env.user.partner_id.id

        leads = request.env['crm.lead'].search([
            ('partner_id', '=', partner_id),
        ])

        return [
            ('res_model', '=', 'crm.lead'),
            ('res_id', 'in', leads.ids),
        ]

    # =========================================================
    # ACTIVITIES LIST
    # =========================================================

    @http.route(
        '/my/crm/activities',
        type='http',
        auth='user',
        website=True
    )
    def crm_activities(self, **kwargs):

        Activity = request.env['mail.activity']

        domain = self._activity_access_domain()

        activities = Activity.sudo().search(
            domain,
            order='date_deadline asc, id asc'
        )

        return request.render(
            'crm_portal.crm_activities',
            {
                'activities': activities,
            }
        )

    # =========================================================
    # ACTIVITY DETAIL
    # =========================================================

    @http.route(
        '/my/crm/activities/<int:activity_id>',
        type='http',
        auth='user',
        website=True
    )
    def crm_activity_detail(self, activity_id, **kwargs):

        Activity = request.env['mail.activity']

        domain = self._activity_access_domain()

        domain.append(
            ('id', '=', activity_id)
        )

        activity = Activity.sudo().search(
            domain,
            limit=1
        )

        if not activity:
            return request.not_found()

        lead = False

        if activity.res_model == 'crm.lead':
            lead = request.env['crm.lead'].sudo().browse(
                activity.res_id
            )

        return request.render(
            'crm_portal.crm_activity_detail',
            {
                'activity': activity,
                'lead': lead,
            }
        )

    # =========================================================
    # MARK ACTIVITY AS DONE
    # =========================================================

    @http.route(
        '/my/crm/activities/<int:activity_id>/done',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def crm_activity_done(self, activity_id, **kwargs):

        Activity = request.env['mail.activity']

        domain = self._activity_access_domain()

        domain.append(
            ('id', '=', activity_id)
        )

        activity = Activity.sudo().search(
            domain,
            limit=1
        )

        if not activity:
            return request.not_found()

        activity.sudo().action_done()

        return request.redirect(
            '/my/crm/activities'
        )