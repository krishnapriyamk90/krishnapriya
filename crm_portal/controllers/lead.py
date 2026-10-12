from odoo import http
from odoo.http import request


class CRMPortalLead(http.Controller):

    # =========================================================
    # ACCESS / VISIBILITY
    # =========================================================

    def _lead_access_domain(self, lead_type='lead'):
        """Admin can access all CRM records.
        Portal users can access only their own records.
        """

        domain = [
            ('type', '=', lead_type),
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
    # LEADS LIST
    # =========================================================

    @http.route(
        '/my/crm/leads',
        type='http',
        auth='user',
        website=True
    )
    def crm_leads(self, **kwargs):

        # -----------------------------------------------------
        # Base domain
        # Admin: all leads
        # Portal user: own leads
        # -----------------------------------------------------

        domain = self._lead_access_domain('lead')

        # -----------------------------------------------------
        # Search parameters
        # -----------------------------------------------------

        search = kwargs.get('search', '').strip()

        try:
            selected_stage = int(kwargs.get('stage_id', 0))
        except (TypeError, ValueError):
            selected_stage = 0

        try:
            page = int(kwargs.get('page', 1))
        except (TypeError, ValueError):
            page = 1

        if page < 1:
            page = 1

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
        # -----------------------------------------------------

        if selected_stage:
            domain.append(
                ('stage_id', '=', selected_stage)
            )

        # -----------------------------------------------------
        # Pagination
        # -----------------------------------------------------

        limit = 10

        total = request.env['crm.lead'].search_count(domain)

        page_count = (total + limit - 1) // limit

        if page_count and page > page_count:
            page = page_count

        offset = (page - 1) * limit

        leads = request.env['crm.lead'].search(
            domain,
            offset=offset,
            limit=limit,
            order='create_date desc'
        )

        # -----------------------------------------------------
        # CRM stages
        # -----------------------------------------------------

        stages = request.env['crm.stage'].search(
            [],
            order='sequence, id'
        )

        return request.render(
            'crm_portal.crm_leads',
            {
                'leads': leads,
                'stages': stages,
                'search': search,
                'selected_stage': selected_stage,
                'total': total,
                'page': page,
                'page_count': page_count,
            }
        )

    # =========================================================
    # LEAD DETAIL
    # =========================================================

    @http.route(
        '/my/crm/leads/<int:lead_id>',
        type='http',
        auth='user',
        website=True
    )
    def crm_lead_detail(self, lead_id, **kwargs):

        # -----------------------------------------------------
        # Admin: all leads
        # Portal user: own leads
        # -----------------------------------------------------

        lead_domain = self._lead_access_domain('lead')

        lead_domain.append(
            ('id', '=', lead_id)
        )

        lead = request.env['crm.lead'].search(
            lead_domain,
            limit=1
        )

        if not lead:
            return request.not_found()

        # -----------------------------------------------------
        # CRM stages
        # Odoo 19 uses team_ids on crm.stage
        # -----------------------------------------------------

        if lead.team_id:

            stages = request.env['crm.stage'].search([
                '|',
                ('team_ids', '=', False),
                ('team_ids', 'in', lead.team_id.id),
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
            ('res_id', '=', lead.id),
        ], order='date_deadline asc')

        return request.render(
            'crm_portal.crm_lead_detail',
            {
                'lead': lead,
                'stages': stages,
                'activities': activities,
            }
        )

    # =========================================================
    # CREATE LEAD - FORM
    # =========================================================

    @http.route(
        '/my/crm/leads/create',
        type='http',
        auth='user',
        website=True,
        methods=['GET']
    )
    def create_lead_form(self, **kwargs):

        return request.render(
            'crm_portal.crm_lead_create'
        )

    # =========================================================
    # CREATE LEAD - SAVE
    # =========================================================

    @http.route(
        '/my/crm/leads/create',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def create_lead(self, **kwargs):

        partner = request.env.user.partner_id

        name = (kwargs.get('name') or '').strip()

        if not name:
            return request.redirect(
                '/my/crm/leads/create'
            )

        # -----------------------------------------------------
        # Prepare values
        # -----------------------------------------------------

        vals = {
            'name': name,
            'type': 'lead',
            'partner_id': partner.id,
            'email_from': (kwargs.get('email_from') or '').strip(),
            'phone': (kwargs.get('phone') or '').strip(),
            'description': kwargs.get('description') or '',
        }

        # -----------------------------------------------------
        # Expected Revenue
        # -----------------------------------------------------

        try:
            vals['expected_revenue'] = float(
                kwargs.get('expected_revenue') or 0
            )
        except (TypeError, ValueError):
            vals['expected_revenue'] = 0.0

        # -----------------------------------------------------
        # Probability
        # -----------------------------------------------------

        try:
            probability = float(
                kwargs.get('probability') or 0
            )
        except (TypeError, ValueError):
            probability = 0.0

        # Keep probability between 0 and 100
        probability = max(0.0, min(100.0, probability))

        vals['probability'] = probability

        # -----------------------------------------------------
        # Expected Closing
        # -----------------------------------------------------

        date_deadline = kwargs.get('date_deadline')

        if date_deadline:
            vals['date_deadline'] = date_deadline

        # -----------------------------------------------------
        # Create lead
        #
        # Portal users do not have general CRM create permission,
        # so sudo() is used after setting the portal user's
        # partner_id explicitly.
        # -----------------------------------------------------

        lead = request.env['crm.lead'].sudo().create(vals)

        return request.redirect(
            '/my/crm/leads/%s' % lead.id
        )

    # =========================================================
    # EDIT LEAD - FORM
    # =========================================================

    @http.route(
        '/my/crm/leads/<int:lead_id>/edit',
        type='http',
        auth='user',
        website=True,
        methods=['GET']
    )
    def edit_lead_form(self, lead_id, **kwargs):

        # -----------------------------------------------------
        # Admin: all leads
        # Portal user: own leads
        # -----------------------------------------------------

        lead_domain = self._lead_access_domain('lead')

        lead_domain.append(
            ('id', '=', lead_id)
        )

        lead = request.env['crm.lead'].search(
            lead_domain,
            limit=1
        )

        if not lead:
            return request.not_found()

        return request.render(
            'crm_portal.crm_lead_edit',
            {
                'lead': lead,
            }
        )

    # =========================================================
    # EDIT LEAD - SAVE
    # =========================================================

    @http.route(
        '/my/crm/leads/<int:lead_id>/edit',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def edit_lead(self, lead_id, **kwargs):

        # -----------------------------------------------------
        # Admin: all leads
        # Portal user: own leads
        # -----------------------------------------------------

        lead_domain = self._lead_access_domain('lead')

        lead_domain.append(
            ('id', '=', lead_id)
        )

        lead = request.env['crm.lead'].search(
            lead_domain,
            limit=1
        )

        if not lead:
            return request.not_found()

        # -----------------------------------------------------
        # Prepare values
        # -----------------------------------------------------

        vals = {
            'name': (kwargs.get('name') or '').strip(),
            'email_from': (kwargs.get('email_from') or '').strip(),
            'phone': (kwargs.get('phone') or '').strip(),
            'description': kwargs.get('description') or '',
        }

        # -----------------------------------------------------
        # Expected Revenue
        # -----------------------------------------------------

        try:
            vals['expected_revenue'] = float(
                kwargs.get('expected_revenue') or 0
            )
        except (TypeError, ValueError):
            vals['expected_revenue'] = 0.0

        # -----------------------------------------------------
        # Probability
        # -----------------------------------------------------

        try:
            probability = float(
                kwargs.get('probability') or 0
            )
        except (TypeError, ValueError):
            probability = 0.0

        probability = max(0.0, min(100.0, probability))

        vals['probability'] = probability

        # -----------------------------------------------------
        # Expected Closing
        # -----------------------------------------------------

        date_deadline = kwargs.get('date_deadline')

        vals['date_deadline'] = date_deadline or False

        # -----------------------------------------------------
        # Update the lead
        #
        # Ownership/access was already checked above.
        # -----------------------------------------------------

        lead.sudo().write(vals)

        return request.redirect(
            '/my/crm/leads/%s' % lead.id
        )

    # =========================================================
    # CHANGE LEAD STAGE
    # =========================================================

    @http.route(
        '/my/crm/leads/<int:lead_id>/stage',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def change_stage(self, lead_id, stage_id=None, **kwargs):

        # -----------------------------------------------------
        # Admin: all leads
        # Portal user: own leads
        # -----------------------------------------------------

        lead_domain = self._lead_access_domain('lead')

        lead_domain.append(
            ('id', '=', lead_id)
        )

        lead = request.env['crm.lead'].search(
            lead_domain,
            limit=1
        )

        if not lead:
            return request.not_found()

        # -----------------------------------------------------
        # Validate stage ID
        # -----------------------------------------------------

        try:
            stage_id = int(stage_id)
        except (TypeError, ValueError):

            return request.redirect(
                '/my/crm/leads/%s' % lead.id
            )

        # -----------------------------------------------------
        # Validate requested CRM stage
        # Odoo 19 uses team_ids on crm.stage
        # -----------------------------------------------------

        if lead.team_id:

            stage = request.env['crm.stage'].search([
                ('id', '=', stage_id),
                '|',
                ('team_ids', '=', False),
                ('team_ids', 'in', lead.team_id.id),
            ], limit=1)

        else:

            stage = request.env['crm.stage'].search([
                ('id', '=', stage_id),
                ('team_ids', '=', False),
            ], limit=1)

        if not stage:

            return request.redirect(
                '/my/crm/leads/%s' % lead.id
            )

        # -----------------------------------------------------
        # Update ONLY the CRM stage
        # -----------------------------------------------------

        lead.sudo().write({
            'stage_id': stage.id,
        })

        return request.redirect(
            '/my/crm/leads/%s' % lead.id
        )

    # =========================================================
    # CONVERT LEAD TO OPPORTUNITY
    # =========================================================

    @http.route(
        '/my/crm/leads/<int:lead_id>/convert',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True
    )
    def convert_to_opportunity(self, lead_id, **kwargs):

        # -----------------------------------------------------
        # Admin: all leads
        # Portal user: own leads
        # -----------------------------------------------------

        lead_domain = self._lead_access_domain('lead')

        lead_domain.append(
            ('id', '=', lead_id)
        )

        lead = request.env['crm.lead'].search(
            lead_domain,
            limit=1
        )

        if not lead:
            return request.not_found()

        # Convert the lead using Odoo CRM's standard conversion logic.
        # sudo() is used because portal users do not have normal
        # CRM write permission.
        lead.sudo().convert_opportunity(
            lead.partner_id
        )

        # Open the converted opportunity
        return request.redirect(
            '/my/crm/opportunities/%s' % lead.id
        )