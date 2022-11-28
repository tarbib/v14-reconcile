###################################################################################
# 
#    Copyright (C) Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMessageNotification(TransactionCase):
    """
    TEST 1 : Notify partners on incoming message with smart notification enabled
        - Processing incoming message
        - Get sent mail message
        - Mail messages count: 2
        - Mail messages #1 recipients: Partner "Demo Notification Type Email"
        - Mail messages #2 recipients count: 2
        - Mail messages #2 recipients: Bob and Mark

    TEST 2 : Notify partners on incoming message with smart notification disabled
        - Processing incoming message
        - Get sent mail message
        - Mail messages count: 2
        - Mail messages #1 recipients: Partner "Demo Notification Type Email"
        - Mail messages #2 recipients count: 4
        - Mail messages #2 recipients: Ann, Bob, Kate, Mark,
    """

    def setUp(self):
        super(TestMessageNotification, self).setUp()
        ResPartner = self.env["res.partner"]
        ResUsers = self.env["res.users"].with_context(mail_create_nolog=True)
        self.IrConfig = self.env["ir.config_parameter"].sudo()
        self.key = "cetmix.mail_incoming_smart_notify"
        self.res_users_internal_user_email = ResUsers.create(
            {
                "name": "Demo Notification Type Email",
                "login": "demo_email",
                "email": "demo.email@example.com",
                "groups_id": [(4, self.ref("base.group_user"))],
                "notification_type": "email",
            }
        )

        self.res_users_internal_user_odoo = ResUsers.create(
            {
                "name": "Demo Notification Type Odoo",
                "login": "demo_odoo",
                "email": "demo.odoo@exmaple.com",
                "groups_id": [(4, self.ref("base.group_user"))],
                "notification_type": "inbox",
            }
        )

        self.res_partner_kate = ResPartner.create(
            {"name": "Kate", "email": "kate@example.com"}
        )
        self.res_partner_ann = ResPartner.create(
            {"name": "Ann", "email": "ann@example.com"}
        )
        self.res_partner_bob = ResPartner.create(
            {"name": "Bob", "email": "bob@example.com"}
        )
        self.res_partner_mark = ResPartner.create(
            {"name": "Mark", "email": "mark@example.com"}
        )

        self.res_partner_target_record = ResPartner.create(
            {"name": "Target", "email": "target@example.com"}
        )
        partner_ids = [
            self.res_partner_kate.id,
            self.res_partner_ann.id,
            self.res_partner_bob.id,
            self.res_partner_mark.id,
        ]
        self.res_partner_target_record.message_subscribe(
            [
                *partner_ids,
                self.res_users_internal_user_email.partner_id.id,
                self.res_users_internal_user_odoo.partner_id.id,
            ],
            [],
        )

        self.message_dict = {
            "message_type": "email",
            "message_id": "<CAFkrrMwZJvtNe6kEM538Xu99TmCn=BgwaLMRMPi+otCSO4G6BQ@mail.example.com>",  # noqa
            "subject": "Test Subject",
            "from": "Mark <mark@example.com>",
            "to": "{} <{}>, {} <{}>".format(*partner_ids),
            "cc": "",
            "email_from": "Mark <mark@exmaple.com>",
            "partner_ids": [self.res_partner_kate.id, self.res_partner_ann.id],
            "date": "2022-06-23 16:52:15",
            "internal": False,
            "body": "",
            "attachments": [],
            "author_id": False,
        }

        # Monkey patch to keep sent mails for further check
        def unlink_replacement(self):
            return

        self.env["mail.mail"]._patch_method("unlink", unlink_replacement)

    def get_incoming_mail(self, state):
        self.IrConfig.set_param(self.key, state)
        target = self.res_partner_target_record
        route = (target._name, target.id, None, self.env.user.id, None)
        self.env["mail.thread"]._message_route_process("", self.message_dict, [route])
        mail_ids = self.env["mail.mail"].search(
            [
                ("res_id", "=", target.id),
                ("model", "=", target._name),
            ]
        )
        self.assertEqual(len(mail_ids), 2, msg="Mail Messages count must be equal to 2")
        internal_partner_mail = mail_ids.filtered(
            lambda mail: len(mail.recipient_ids) == 1
        )
        partner_mail = mail_ids.filtered(
            lambda mail: mail.id != internal_partner_mail.id
        )
        return internal_partner_mail, partner_mail

    # -- TEST 1 : Notify partners on incoming message with smart notification enabled
    def test_enable_smart_notification(self):
        """
        Notify partners on incoming message
        with smart notification enabled
        """

        # Processing incoming message
        # Get sent mail message
        # Mail messages count: 2
        # Mail messages #1 recipients: Partner "Demo Notification Type Email"
        # Mail messages #2 recipients count: 2
        # Mail messages #2 recipients: Bob and Mark
        internal_partner_mail, partner_mail = self.get_incoming_mail(True)
        self.assertEqual(
            internal_partner_mail.recipient_ids,
            self.res_users_internal_user_email.partner_id,
            msg="Mail recipient must be equal only "
            "internal partner (notification type == Email)",
        )
        recipients_ids = partner_mail.recipient_ids.ids
        self.assertEqual(
            len(recipients_ids), 2, msg="Recipients count must be equal to 2"
        )
        self.assertNotIn(
            self.res_users_internal_user_email.partner_id.id,
            recipients_ids,
            msg="Message recipients must contain internal partner (odoo)",
        )
        self.assertIn(
            self.res_partner_bob.id,
            recipients_ids,
            msg="Message recipients must contain partner Bob",
        )
        self.assertIn(
            self.res_partner_mark.id,
            recipients_ids,
            msg="Message recipients must contain partner Mark",
        )

    # -- TEST 2 : Notify partners on incoming message with smart notification disabled
    def test_disable_smart_notification(self):
        """
        Notify partners on incoming message
        with smart notification disabled
        """

        # Processing incoming message
        # Get sent mail message
        # Mail messages count: 2
        # Mail messages #1 recipients: Partner "Demo Notification Type Email"
        # Mail messages #2 recipients count: 4
        # Mail messages #2 recipients: Ann, Bob, Kate, Mark,
        internal_partner_mail, partner_mail = self.get_incoming_mail(False)
        self.assertEqual(
            internal_partner_mail.recipient_ids,
            self.res_users_internal_user_email.partner_id,
            msg="Mail recipient must be equal only "
            "internal partner (notification type == Email)",
        )
        self.assertEqual(
            len(partner_mail.recipient_ids),
            4,
            msg="Recipients count must be equal to 4",
        )
        recipients_ids = partner_mail.recipient_ids.ids
        self.assertIn(
            self.res_partner_ann.id,
            recipients_ids,
            msg="Message recipients must contain partner Ann",
        )
        self.assertIn(
            self.res_partner_bob.id,
            recipients_ids,
            msg="Message recipients must contain partner Bob",
        )
        self.assertIn(
            self.res_partner_kate.id,
            recipients_ids,
            msg="Message recipients must contain partner Kate",
        )
        self.assertIn(
            self.res_partner_mark.id,
            recipients_ids,
            msg="Message recipients must contain partner Mark",
        )
