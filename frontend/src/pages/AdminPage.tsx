import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { usersAPI, glGroupsAPI } from '../services/api';

const MODULES = ['inventory', 'sales', 'purchasing', 'manufacturing', 'quality', 'reporting', 'admin'];
const ACTIONS = ['create', 'read', 'update', 'delete', 'approve', 'export'];

const AdminPage: React.FC = () => {
  const [tab, setTab] = useState<'users' | 'groups' | 'gl-groups'>('users');
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [showCreateGL, setShowCreateGL] = useState(false);
  const [userForm, setUserForm] = useState({ username: '', email: '', password: '', full_name: '' });
  const [groupForm, setGroupForm] = useState({ name: '', description: '' });
  const [glForm, setGlForm] = useState({ name: '', description: '', account_mappings: [] as any[] });
  const queryClient = useQueryClient();

  const { data: users } = useQuery({ queryKey: ['users'], queryFn: () => usersAPI.list() });
  const { data: groups } = useQuery({ queryKey: ['groups'], queryFn: () => usersAPI.listGroups() });
  const { data: glGroups } = useQuery({ queryKey: ['gl-groups'], queryFn: () => glGroupsAPI.list() });

  const createUser = useMutation({
    mutationFn: (data: any) => usersAPI.create(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['users'] }); setShowCreateUser(false); toast.success('User created'); },
    onError: () => toast.error('Failed to create user'),
  });

  const createGroup = useMutation({
    mutationFn: (data: any) => usersAPI.createGroup(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['groups'] }); setShowCreateGroup(false); toast.success('Group created'); },
    onError: () => toast.error('Failed to create group'),
  });

  const createGL = useMutation({
    mutationFn: (data: any) => glGroupsAPI.create(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['gl-groups'] }); setShowCreateGL(false); toast.success('GL Group created'); },
    onError: () => toast.error('Failed to create GL Group'),
  });

  return (
    <div>
      <PageHeader
        title="Administration"
        subtitle="Manage users, groups, permissions, and GL groups"
        actions={
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => tab === 'users' ? setShowCreateUser(true) : tab === 'groups' ? setShowCreateGroup(true) : setShowCreateGL(true)}>
              New {tab === 'users' ? 'User' : tab === 'groups' ? 'Group' : 'GL Group'}
            </button>
          </div>
        }
      />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {([['users', 'Users'], ['groups', 'Groups & Permissions'], ['gl-groups', 'GL Groups']] as const).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id as any)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {label}
          </button>
        ))}
      </div>

      <div className="card">
        {tab === 'users' && (
          <DataTable
            columns={[
              { header: 'Username', accessor: 'username' },
              { header: 'Name', accessor: 'full_name' },
              { header: 'Email', accessor: 'email' },
              { header: 'Admin', accessor: (r: any) => r.is_superuser ? <span className="badge-blue">Superuser</span> : '' },
              { header: 'Status', accessor: (r: any) => <span className={r.is_active ? 'badge-green' : 'badge-red'}>{r.is_active ? 'Active' : 'Disabled'}</span> },
            ]}
            data={users?.data || []}
          />
        )}
        {tab === 'groups' && (
          <DataTable
            columns={[
              { header: 'Name', accessor: 'name' },
              { header: 'Description', accessor: 'description' },
            ]}
            data={groups?.data || []}
          />
        )}
        {tab === 'gl-groups' && (
          <DataTable
            columns={[
              { header: 'Name', accessor: 'name' },
              { header: 'Description', accessor: 'description' },
              { header: 'Accounts', accessor: (r: any) => r.account_mappings?.length || 0 },
            ]}
            data={glGroups?.data || []}
          />
        )}
      </div>

      {/* Create User Modal */}
      <Modal isOpen={showCreateUser} onClose={() => setShowCreateUser(false)} title="Create User">
        <form onSubmit={(e) => { e.preventDefault(); createUser.mutate(userForm); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Username</label>
              <input className="input-field" value={userForm.username} onChange={(e) => setUserForm({ ...userForm, username: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Full Name</label>
              <input className="input-field" value={userForm.full_name} onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input className="input-field" type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Password</label>
              <input className="input-field" type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} required />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowCreateUser(false)}>Cancel</button>
            <button type="submit" className="btn-primary">Create</button>
          </div>
        </form>
      </Modal>

      {/* Create Group Modal */}
      <Modal isOpen={showCreateGroup} onClose={() => setShowCreateGroup(false)} title="Create Group">
        <form onSubmit={(e) => { e.preventDefault(); createGroup.mutate(groupForm); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input className="input-field" value={groupForm.name} onChange={(e) => setGroupForm({ ...groupForm, name: e.target.value })} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea className="input-field" rows={3} value={groupForm.description} onChange={(e) => setGroupForm({ ...groupForm, description: e.target.value })} />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowCreateGroup(false)}>Cancel</button>
            <button type="submit" className="btn-primary">Create</button>
          </div>
        </form>
      </Modal>

      {/* Create GL Group Modal */}
      <Modal isOpen={showCreateGL} onClose={() => setShowCreateGL(false)} title="Create GL Group" size="lg">
        <form onSubmit={(e) => { e.preventDefault(); createGL.mutate(glForm); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input className="input-field" value={glForm.name} onChange={(e) => setGlForm({ ...glForm, name: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input className="input-field" value={glForm.description} onChange={(e) => setGlForm({ ...glForm, description: e.target.value })} />
            </div>
          </div>
          <div>
            <h4 className="text-sm font-medium mb-2">Account Mappings</h4>
            {['sales', 'cogs', 'inventory_asset', 'inventory_adjustment'].map((type) => (
              <div key={type} className="grid grid-cols-3 gap-2 mb-2">
                <span className="text-sm text-gray-600 self-center capitalize">{type.replace('_', ' ')}</span>
                <input
                  className="input-field text-sm"
                  placeholder="Account name"
                  onChange={(e) => {
                    const mappings = glForm.account_mappings.filter(m => m.account_type !== type);
                    if (e.target.value) mappings.push({ account_type: type, account_name: e.target.value });
                    setGlForm({ ...glForm, account_mappings: mappings });
                  }}
                />
                <input className="input-field text-sm" placeholder="Account #" />
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowCreateGL(false)}>Cancel</button>
            <button type="submit" className="btn-primary">Create</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default AdminPage;
