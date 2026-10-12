from odoo import http
from odoo.http import request


class CRMPortalOpportunity(http.Controller):

    # =========================================================
    # ACCESS / VISIBILITY
    # =========================================================

    def _opportunity_access_domain(self):
        """Admin can access all opportunities.
        Portal users can access only their own opportunities.
        """

        domain = [
            ('type', '=', 'opportunity'),
        ]

        if not request.env.user.has_group('base.group_system'):
            domain.append(
                (
                    'partner_id',
                    '=',
                    request.env.user.partner_id.id,
                )
            )

        return domain

    # =========================================================
    # OPPORTUNITIES LIST
    # =========================================================
    # =========================================================
    # OPPORTUNITIES LIST
    # =========================================================

    @http.route(
        '/my/crm/opportunities',
        type='http',
        auth='user',
        website=True
    )
    def crm_opportunities(self, **kwargs):

        domain = self._opportunity_access_domain()

        search = (kwargs.get('search') or '').strip()

        # -----------------------------------------------------
        # Read the selected filter
        # "lost" is a status filter, not a CRM stage.
        # -----------------------------------------------------

        selected_stage_raw = kwargs.get('stage_id', '')

        lost_filter = selected_stage_raw == 'lost'

        try:
            selected_stage = (
                int(selected_stage_raw)
                if selected_stage_raw and not lost_filter
                else 0
            )
        except (TypeError, ValueError):
            selected_stage = 0

        try:
            page = int(kwargs.get('page', 1))
        except (TypeError, ValueError):
            page = 1

        if page < 1:
            page = 1

        # -----------------------------------------------------
        # Active / Lost filter
        # Lost opportunities are archived by Odoo.
        # -----------------------------------------------------

        if lost_filter:
            domain += [
                ('active', '=', False),
                ('probability', '=', 0),
            ]
        else:
            domain.append(('active', '=', True))

        # -----------------------------------------------------
        # Search
        # -----------------------------------------------------

        if search:
            domain += [
                '|',
                '|',
                ('name', 'ilike', search),
                ('email_from', 'ilike', search),
                ('phone', 'ilike', search),
            ]

        # -----------------------------------------------------
        # Stage filter
        # Apply a stage only when a real stage was selected.
        # -----------------------------------------------------

        if selected_stage:
            domain.append(
                ('stage_id', '=', selected_stage)
            )

        # -----------------------------------------------------
        # Include archived records in the query.
        # The domain above still determines which are shown.
        # -----------------------------------------------------

        Lead = request.env['crm.lead'].with_context(
            active_test=False
        )

        # -----------------------------------------------------
        # Pagination
        # -----------------------------------------------------

        limit = 10

        total = Lead.search_count(domain)

        page_count = (total + limit - 1) // limit

        if page_count and page > page_count:
            page = page_count

        offset = (page - 1) * limit

        opportunities = Lead.search(
            domain,
            offset=offset,
            limit=limit,
            order='create_date desc'
        )

        # -----------------------------------------------------
        # Real CRM stages only
        # Lost is deliberately NOT added to this list.
        # -----------------------------------------------------

        stages = request.env['crm.stage'].search(
            [],
            order='sequence, id'
        )

        return request.render(
            'crm_portal.crm_opportunities',
            {
                'opportunities': opportunities,
                'stages': stages,
                'search': search,
                'selected_stage': selected_stage,
                'lost_filter': lost_filter,
                'total': total,
                'page': page,
                'page_count': page_count,
            }
        )

    # =========================================================
    # OPPORTUNITY DETAIL
    # =========================================================

    @http.route(
        '/my/crm/opportunities/<int:opportunity_id>',
        type='http',
        auth='user',
        website=True
    )
    def crm_opportunity_detail(self, opportunity_id, **kwargs):

        # -----------------------------------------------------
        # Admin: all opportunities
        # Portal user: own opportunities
        # -----------------------------------------------------

        opportunity_domain = self._opportunity_access_domain()

        opportunity_domain.append(
            ('id', '=', opportunity_id)
        )

        opportunity = request.env['crm.lead'].with_context(
            active_test=False
        ).search(
            opportunity_domain,
            limit=1
        )

        if not opportunity:
            return request.not_found()

        # -----------------------------------------------------
        # CRM stages
        # -----------------------------------------------------

        if opportunity.team_id:

            stages = request.env['crm.stage'].search([
                '|',
                ('team_ids', '=', False),
                ('team_ids', 'in', opportunity.team_id.id),
            ], order='sequence, id')

        else:

            stages = request.env['crm.stage'].search(
                [('team_ids', '=', False)],
                order='sequence, id'
            )

        # -----------------------------------------------------
        # Activities
        # -----------------------------------------------------

        activities = request.env['mail.activity'].sudo().search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', opportunity.id),
        ], order='date_deadline asc')
        lost_reasons = request.env['crm.lost.reason'].sudo().search(
            [],
            order='id'
        )
        return request.render(
            'crm_portal.crm_opportunity_detail',
            {
                'opportunity': opportunity,
                'stages': stages,
                'activities': activities,
                'lost_reasons': lost_reasons,
            }
        )

    # =========================================================
    # CHANGE OPPORTUNITY STAGE
    # =========================================================

    @http.route(
        '/my/crm/opportunities/<int:opportunity_id>/stage',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def change_opportunity_stage(
        self,
        opportunity_id,
        stage_id=None,
        **kwargs
    ):

        # -----------------------------------------------------
        # Admin: all opportunities
        # Portal user: own opportunities
        # -----------------------------------------------------

        opportunity_domain = self._opportunity_access_domain()

        opportunity_domain.append(
            ('id', '=', opportunity_id)
        )

        opportunity = request.env['crm.lead'].search(
            opportunity_domain,
            limit=1
        )

        if not opportunity:
            return request.not_found()

        try:
            stage_id = int(stage_id)
        except (TypeError, ValueError):

            return request.redirect(
                '/my/crm/opportunities/%s' % opportunity.id
            )

        # -----------------------------------------------------
        # Validate stage against the opportunity's team
        # -----------------------------------------------------

        if opportunity.team_id:

            stage = request.env['crm.stage'].search([
                ('id', '=', stage_id),
                '|',
                ('team_ids', '=', False),
                ('team_ids', 'in', opportunity.team_id.id),
            ], limit=1)

        else:

            stage = request.env['crm.stage'].search([
                ('id', '=', stage_id),
                ('team_ids', '=', False),
            ], limit=1)

        if not stage:

            return request.redirect(
                '/my/crm/opportunities/%s' % opportunity.id
            )

        # -----------------------------------------------------
        # Update only the stage
        # -----------------------------------------------------

        opportunity.sudo().write({
            'stage_id': stage.id,
        })

        return request.redirect(
            '/my/crm/opportunities/%s' % opportunity.id
        )

    # =========================================================
    # EDIT OPPORTUNITY - FORM
    # =========================================================

    @http.route(
        '/my/crm/opportunities/<int:opportunity_id>/edit',
        type='http',
        auth='user',
        website=True,
        methods=['GET']
    )
    def edit_opportunity_form(
        self,
        opportunity_id,
        **kwargs
    ):

        # -----------------------------------------------------
        # Admin: all opportunities
        # Portal user: own opportunities
        # -----------------------------------------------------

        opportunity_domain = self._opportunity_access_domain()

        opportunity_domain.append(
            ('id', '=', opportunity_id)
        )

        opportunity = request.env['crm.lead'].search(
            opportunity_domain,
            limit=1
        )

        if not opportunity:
            return request.not_found()

        return request.render(
            'crm_portal.crm_opportunity_edit',
            {
                'opportunity': opportunity,
            }
        )

    # =========================================================
    # EDIT OPPORTUNITY - SAVE
    # =========================================================

    @http.route(
        '/my/crm/opportunities/<int:opportunity_id>/edit',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def edit_opportunity(
        self,
        opportunity_id,
        **kwargs
    ):

        # -----------------------------------------------------
        # Admin: all opportunities
        # Portal user: own opportunities
        # -----------------------------------------------------

        opportunity_domain = self._opportunity_access_domain()

        opportunity_domain.append(
            ('id', '=', opportunity_id)
        )

        opportunity = request.env['crm.lead'].search(
            opportunity_domain,
            limit=1
        )

        if not opportunity:
            return request.not_found()

        vals = {
            'name': (kwargs.get('name') or '').strip(),
            'email_from': (kwargs.get('email_from') or '').strip(),
            'phone': (kwargs.get('phone') or '').strip(),
            'description': kwargs.get('description') or '',
        }

        try:
            vals['expected_revenue'] = float(
                kwargs.get('expected_revenue') or 0
            )
        except (TypeError, ValueError):
            vals['expected_revenue'] = 0.0

        try:
            probability = float(
                kwargs.get('probability') or 0
            )
        except (TypeError, ValueError):
            probability = 0.0

        vals['probability'] = max(
            0.0,
            min(100.0, probability)
        )

        vals['date_deadline'] = (
            kwargs.get('date_deadline') or False
        )

        opportunity.sudo().write(vals)

        return request.redirect(
            '/my/crm/opportunities/%s' % opportunity.id
        )
    # =========================================================
    # MARK OPPORTUNITY AS LOST
    # =========================================================

    @http.route(
        '/my/crm/opportunities/<int:opportunity_id>/lost',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def mark_opportunity_lost(
        self,
        opportunity_id,
        lost_reason_id=None,
        **kwargs
    ):

        # -----------------------------------------------------
        # ACCESS CHECK
        # Admin: all opportunities
        # Portal user: own opportunities
        # -----------------------------------------------------

        opportunity_domain = self._opportunity_access_domain()

        opportunity_domain.append(
            ('id', '=', opportunity_id)
        )

        opportunity = request.env['crm.lead'].search(
            opportunity_domain,
            limit=1
        )

        if not opportunity:
            return request.not_found()

        # -----------------------------------------------------
        # Do not mark an already-Won opportunity as Lost
        # -----------------------------------------------------

        if opportunity.stage_id.is_won:
            return request.redirect(
                '/my/crm/opportunities/%s' % opportunity.id
            )

        # -----------------------------------------------------
        # Validate the selected Lost Reason
        # -----------------------------------------------------

        lost_reason = False

        if lost_reason_id:
            try:
                lost_reason_id = int(lost_reason_id)
            except (TypeError, ValueError):
                return request.redirect(
                    '/my/crm/opportunities/%s' % opportunity.id
                )

            lost_reason = request.env['crm.lost.reason'].sudo().search(
                [('id', '=', lost_reason_id)],
                limit=1
            )

            if not lost_reason:
                return request.redirect(
                    '/my/crm/opportunities/%s' % opportunity.id
                )

        # -----------------------------------------------------
        # Use Odoo's standard Lost functionality
        # -----------------------------------------------------

        opportunity.sudo().action_set_lost(
            lost_reason_id=lost_reason.id if lost_reason else False
        )

        # -----------------------------------------------------
        # Return to the active opportunities list
        # -----------------------------------------------------

        return request.redirect(
            '/my/crm/opportunities'
        )