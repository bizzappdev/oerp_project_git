# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp.osv import fields
import logging

_logger = logging.getLogger(__name__)

try:
    import git
except ImportError:
    _logger.warning("Please install GitPython==0.3.2")

import os


def get_diff_html(base_commit, main_commit=False):
    if not main_commit:
        if base_commit.parents:

            diff_objs = base_commit.parents[0].diff(base_commit,
                                                    create_patch=True)
        else:
            diff_objs = base_commit.diff(base_commit, create_patch=True)
    else:
        diff_objs = base_commit.diff(main_commit, create_patch=True)

    final_string = ""
    for diff_obj in diff_objs:
        if diff_obj.deleted_file:
            if not diff_obj.diff.strip():
                final_string += "\n\n--- %s" % diff_obj.a_blob.path
            else:
                final_string += "\n\n%s" % diff_obj.diff
        elif diff_obj.new_file and not diff_obj.diff:
            final_string += "\n\n+++ %s" % diff_obj.a_blob.path

        else:
            final_string += "\n\n%s" % diff_obj.diff

    final_string = final_string.strip()
    raw_html = []
    for text in final_string.split("\n"):
        text = (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("\n", "&para;<br>"))
        if text.startswith("+"):
            raw_html.append(
                "<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
        elif text.startswith("-"):
            raw_html.append(
                "<del style=\"background:#ffe6e6;\">%s</del>" % text)
        else:
            raw_html.append("<spam>%s</spam>" % text)

    html_string = """
        <html>
        <body>
        <pre>%s</pre>
        </body>
        </html>
    """ % '<br/>'.join(raw_html)

    return html_string


class git_setting(osv.osv):
    _name = 'git.setting'
    _description = 'Git setting'

    _columns = {
        'name': fields.char("Name", size=64, help="Name of the setting To"),
        'username': fields.char('Username', size=64,
                                help="username of the Git repo"),
        'password': fields.char('Password', size=64,
                                help="Password for Git repo"),
        'git_folder': fields.char('Git Folder', size=256,
                                  help="Static Folder from Sever which have"
                                  " write access for openerp users"),
    }

    def get_url(self, git_url, user_name, password):
        if '@' in git_url:
            git_url = git_url.replace("@", ":%s@" % password)
        else:
            git_url = git_url.replace("//", "//%s:%s@" % (user_name, password))
        return git_url

    def clone_project(self, cr, uid, ids, project_data, context={}):
        for self_rec in self.browse(cr, uid, ids, context=context):
            git_url = self.get_url(project_data['git_url'], self_rec.username,
                                   self_rec.password)
            git_repo = git.Git()
            project_path = os.path.join(
                self_rec.git_folder,
                project_data['git_url'].split("/")[-1].split(".")[0])
            if os.path.exists(project_path):
                continue
            git_repo.clone(git_url, project_path)

        return True

    def pull_project(self, cr, uid, ids, project_data, context={}):
        for self_rec in self.browse(cr, uid, ids, context=context):
            project_path = os.path.join(
                self_rec.git_folder,
                project_data['git_url'].split("/")[-1].split(".")[0])
            if os.path.exists(project_path):
                git_pro = git.Repo(project_path)
                try:
                    git_pro.remotes.origin.pull()
                except:
                    pass

        return True

    def git_clone_pull(self, cr, uid, ids, project_data, context={}):
        pro_pool = self.pool.get('git.project')
        for self_rec in self.browse(cr, uid, ids, context=context):
            project_path = os.path.join(
                self_rec.git_folder,
                project_data['git_url'].split("/")[-1].split(".")[0])
            if os.path.exists(project_path):
                self.pull_project(cr, uid, [self_rec.id], project_data,
                                  context=context)
            else:
                self.clone_project(cr, uid, [self_rec.id], project_data,
                                   context=context)
            if not project_data['git_project_id']:
                cr_id = pro_pool.create(cr, uid, {
                    'git_path': project_data['git_url'],
                    'project_id': project_data['id'],
                    'git_setting_id': self_rec.id
                })
                self.pool.get('project.project').write(
                    cr, uid, project_data['id'], {'git_project_id': cr_id})
        return True

    def get_all_commits(self, cr, uid, ids, project, context={}):
        br_pool = self.pool.get('git.branch')
        cr_pool = self.pool.get('git.commit')
        for self_rec in self.browse(cr, uid, ids, context=context):
            project_path = os.path.join(
                self_rec.git_folder,
                project.git_path.split("/")[-1].split(".")[0])

            git_repo = git.Repo(project_path)
            git_pro_id = project.git_project_id.id
            for branches in git_repo.remote().refs:
                br_ids = br_pool.search(cr, uid,
                                        [('name', '=', branches.name),
                                         ('git_project_id', '=', git_pro_id)])
                if not br_ids:
                    br_ids = [br_pool.create(cr, uid, {
                        'name': branches.name,
                        'git_project_id': git_pro_id,
                    })]
                for commit in git_repo.iter_commits(branches.name):
                    cr_ids = cr_pool.search(cr, uid,
                                            [('name', '=', commit.hexsha)])
                    if cr_ids:
                        br_pool.write(cr, uid, br_ids,
                                      {'commit_ids': [(4, cr_ids[0])]})
                        continue
                    diff = get_diff_html(commit)
                    cr_ids = [cr_pool.create(
                        cr, uid, {
                            'name':commit.hexsha,
                            'message': commit.message,
                            'author': str(commit.author),
                            'git_id': self_rec.id,
                            'diff': diff,
                        })]
                    br_pool.write(cr, uid, br_ids,
                                  {'commit_ids': [(4, cr_ids[0])]})
        return True

git_setting()


class git_project(osv.osv):
    _name = 'git.project'
    _rec_name = "project_id"

    _columns = {
        'git_path': fields.char('Git Repository', size=256),
        'project_id': fields.many2one('project.project', 'Project'),
        'git_setting_id': fields.many2one('git.setting', 'Git Setting'),
        'branch_ids': fields.one2many('git.branch', 'git_project_id',
                                      'Branches'),

    }

git_project()


class project_project(osv.osv):
    _inherit = 'project.project'

    _columns = {
        'git_setting_id': fields.many2one('git.setting', 'Git Setting'),
        'git_project_id': fields.many2one('git.project', 'Git project'),
        'branch_id': fields.many2one('git.branch', 'Branch'),
        'commit_ids': fields.one2many('git.commit', 'project_id', 'Commits'),
        'git_path': fields.char(
            'Git Repository', size=256,
            help="Git URL for the specific git repo e.g "
            "https://BizzAppDev@bitbucket.org/BizzAppDev/oerp_project_git.git")
    }

    def onchange_branch(self, cr, uid, ids, branch_id, commit_ids, context={}):

        res = {'value': {}}
        if not branch_id:
            res['value']['commit_ids'] = []
            return res
        br_pool = self.pool.get('git.branch')
        cr_pool = self.pool.get('git.commit')
        if commit_ids:
            commit_ids = [x[1] for x in commit_ids]
            cr_pool.write(cr, uid, commit_ids, {'project_id': False})
        br_objs = br_pool.browse(cr, uid, branch_id)
        cr_ids = [x.id for x in br_objs.commit_ids]
        res['value']['commit_ids'] = cr_ids

        return res

    def get_git_repo(self, cr, uid, ids, context={}):
        sett_pool = self.pool.get('git.setting')
        set_ids = sett_pool.search(cr, uid, [])
        for self_rec in self.browse(cr, uid, ids, context=context):
            sett_pool.git_clone_pull(
                cr, uid, set_ids,
                {
                    'git_url': self_rec.git_path, 'id': self_rec.id,
                    'git_project_id': (self_rec.git_project_id and
                                       self_rec.git_project_id.id or False)
                })
            cr.commit()
            self_rec = self.browse(cr, uid, self_rec.id, context=context)
            sett_pool.get_all_commits(cr, uid, set_ids, self_rec,
                                      context=context)
        return True

    def get_all_commits(self, cr, uid, ids, context={}):
        sett_pool = self.pool.get('git.setting')
        set_ids = sett_pool.search(cr, uid, [])
        for self_rec in self.browse(cr, uid, ids, context=context):
            sett_pool.get_commits(cr, uid, set_ids, self_rec, context=context)
        return True

project_project()


class git_branch(osv.osv):
    _name = 'git.branch'
    _columns = {
        'name': fields.char('Branch Name', size=256),
        'git_project_id': fields.many2one('git.project', 'Git project'),
        'commit_ids': fields.many2many('git.commit', 'git_branch_commit_rel',
                                       'branch_id', 'commit_id', 'Commits'),
    }

git_branch()


class git_commit(osv.osv):
    _name = 'git.commit'
    _description = 'Git setting'
    _rec_name = "display_name"

    def _get_display_name(self, cr, uid, ids, name, arg, context={}):
        ret_val = {}
        for self_rec in self.browse(cr, uid, ids, context=context):
            ret_val[self_rec.id] = self_rec.name[:8]
        return ret_val

    _columns = {
        'git_id': fields.many2one("git.setting", "Project",
                                  ondelete='cascade'),
        'display_name': fields.function(
            _get_display_name, method=True, string='SHA',
            type='char', store=False, size=256),
        'name': fields.char('SHA', size=256, required=True),
        'author': fields.char('Author', size=256, required=True, select=True),
        'message': fields.char('Message', size=256, required=True,
                               select=True),
        'project_id': fields.many2one('project.project', 'Projects'),
        'diff': fields.html('diff'),
    }

git_commit()


class project_task(osv.osv):
    _inherit = 'project.task'

    def _get_related_commit(self, cr, uid, ids, name, arg, context={}):
        ret_val = {}
        for self_rec in self.browse(cr, uid, ids, context=context):
            ret_val[self_rec.id] = []
            git_project = self_rec.project_id.git_project_id
            if not git_project:
                continue
            ret_val[self_rec.id] = []
            commits = [y for x in git_project.branch_ids for y in x.commit_ids]

            for commit in commits:
                if self_rec.name.lower() in commit.message.lower() or \
                        '%s' % self_rec.tracking_number in commit.message or \
                        '#%s' % self_rec.id in commit.message:
                    ret_val[self_rec.id].append(commit.id)
            ret_val[self_rec.id] = list(set(ret_val[self_rec.id]))

        return ret_val

    _columns = {
        'tracking_number': fields.char('Tracking Number', size=16,
                                       help="Mention this number in commit"),
        'related_commit_ids': fields.function(
            _get_related_commit, method=True, string='Related commit',
            type='many2many', relation="git.commit", store=False),
    }

    def create(self, cr, uid, values, context=None):
        """
        #TODO make doc string
        Comment this
        """
        if context is None:
            context = {}
        #TODO : process on result
        values['tracking_number'] = self.pool.get('ir.sequence').get(
            cr, uid, 'project.task.tracking')
        return super(project_task, self).create(cr, uid,
                                                values, context=context)

project_task()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
