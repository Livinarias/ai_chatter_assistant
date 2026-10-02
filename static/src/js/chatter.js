/** @odoo-module **/

import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.isAiLoading = false;
    },

    async _onAiSummarize() {
        if (this.isAiLoading || !this.props.threadId || !this.props.threadModel) {
            return;
        }
        this.isAiLoading = true;
        try {
            await this.orm.call(
                this.props.threadModel,
                "action_ai_summarize",
                [[this.props.threadId]]
            );
            if (this.thread && typeof this.thread.fetchNewMessages === "function") {
                await this.thread.fetchNewMessages();
            }
        } catch (error) {
            const message = error?.data?.message || error?.message || "Error generating summary";
            this.notification.add(message, { type: "danger" });
        } finally {
            this.isAiLoading = false;
        }
    },

    async _onAiReply() {
        if (!this.props.threadId || !this.props.threadModel) {
            return;
        }
        await this.action.doAction({
            name: "AI Reply Assistant",
            type: "ir.actions.act_window",
            res_model: "ai.reply.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_source_model: this.props.threadModel,
                default_source_id: this.props.threadId,
            },
        });
    },

    async _onAiCreateLead() {
        if (this.isAiLoading || !this.props.threadId || !this.props.threadModel) {
            return;
        }
        this.isAiLoading = true;
        try {
            this.notification.add("Analizando conversación y generando Lead con IA...", { type: "info" });
            const result = await this.orm.call(
                "crm.lead",
                "action_ai_create_lead_from_thread",
                [],
                {
                    source_model: this.props.threadModel,
                    source_id: this.props.threadId,
                }
            );
            if (result && result.lead_id) {
                this.notification.add("¡Lead creado exitosamente con IA! 🎯", { type: "success" });
                await this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "crm.lead",
                    res_id: result.lead_id,
                    views: [[false, "form"]],
                    target: "current",
                });
            }
        } catch (error) {
            const message = error?.data?.message || error?.message || "Error creating CRM lead with AI";
            this.notification.add(message, { type: "danger" });
        } finally {
            this.isAiLoading = false;
        }
    },
});
