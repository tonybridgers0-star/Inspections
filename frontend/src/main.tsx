import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Button, Container, MenuItem, Select, Stack, TextField, Typography } from '@mui/material'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const api = axios.create({ baseURL: 'http://127.0.0.1:8000' })
const queryClient = new QueryClient()

type Order = { id: string; order_number: string; insured_name?: string; status: string; address1?: string; city?: string; state?: string; lat?: number; lon?: number }

function App() {
  const qc = useQueryClient()
  const [viewId, setViewId] = React.useState('')
  const [viewName, setViewName] = React.useState('Active Only')
  const { data: views = [] } = useQuery({ queryKey: ['views'], queryFn: async () => (await api.get('/views')).data })
  const { data: orders = [] } = useQuery<Order[]>({ queryKey: ['orders', viewId], queryFn: async () => (await api.get('/orders', { params: { view_id: viewId || undefined } })).data })

  const complete = useMutation({
    mutationFn: async (id: string) => api.post(`/orders/${id}/complete`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] })
  })

  const saveView = useMutation({
    mutationFn: async () => api.post('/views', { name: viewName, filters: { rules: [{ field: 'status', op: 'eq', value: 'Active' }] }, columns: ['order_number', 'insured_name', 'status'], sorts: [] }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['views'] })
  })

  const bulkGeocode = useMutation({ mutationFn: async () => api.post('/geocode/bulk', null, { params: { view_id: viewId || undefined } }) })

  return <Container>
    <Typography variant='h4' sx={{ my: 2 }}>Inspection Order Manager</Typography>
    <Stack direction='row' spacing={1} sx={{ mb: 2 }}>
      <Select value={viewId} displayEmpty onChange={(e) => setViewId(e.target.value)}>
        <MenuItem value=''>All Orders</MenuItem>
        {views.map((v: any) => <MenuItem key={v.id} value={v.id}>{v.name}</MenuItem>)}
      </Select>
      <TextField size='small' value={viewName} onChange={(e) => setViewName(e.target.value)} />
      <Button variant='contained' onClick={() => saveView.mutate()}>Save Active View</Button>
      <Button onClick={() => bulkGeocode.mutate()}>Bulk geocode current view</Button>
    </Stack>
    <table border={1} cellPadding={6} style={{ width: '100%', marginBottom: 12 }}>
      <thead><tr><th>Order #</th><th>Insured</th><th>Status</th><th>Address</th><th>Action</th></tr></thead>
      <tbody>
        {orders.map((o) => <tr key={o.id}><td>{o.order_number}</td><td contentEditable suppressContentEditableWarning>{o.insured_name}</td><td>{o.status}</td><td>{o.address1}, {o.city}</td><td><Button size='small' onClick={() => complete.mutate(o.id)}>Complete</Button></td></tr>)}
      </tbody>
    </table>

    <MapContainer style={{ height: 420 }} center={[37.8, -96]} zoom={4}>
      <TileLayer attribution='&copy; OpenStreetMap contributors' url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png' />
      {orders.filter((o) => o.lat && o.lon && o.status !== 'Completed').map((o) => (
        <Marker key={o.id} position={[o.lat!, o.lon!]}>
          <Popup>
            <div>
              <strong>{o.order_number}</strong><br />
              {o.address1}
              <Button size='small' onClick={() => complete.mutate(o.id)}>Complete</Button>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  </Container>
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
)
